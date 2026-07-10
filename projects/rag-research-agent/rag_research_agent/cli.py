from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from .answer import AnswerResult, answer_query
from .config import load_model_config
from .documents import load_documents
from .index import build_index_from_documents
from .retrieve import RetrievalResult, retrieve
from .tracing import (
    JsonlTracer,
    elapsed_ms,
    emit_trace,
    new_rag_run_id,
    summarize_answer_result,
    summarize_retrieval_results,
)


DEFAULT_DATA_PATH = Path("data/raw")
DEFAULT_CHUNK_SIZE = 300
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_TOP_K = 3
DEFAULT_MIN_SCORE = 0.5
DEFAULT_TRACE_PATH = Path("traces/rag.jsonl")
DEFAULT_EVAL_CASES_PATH = Path("evals/cases.yaml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rag-research-agent",
        description="Ask questions over local documents with retrieval and citations.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="Ask one question over local documents.")
    ask_parser.add_argument("query", help="Question to answer from the document collection.")
    ask_parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Directory containing source documents.",
    )
    ask_parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Maximum characters per chunk.",
    )
    ask_parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help="Overlapping characters between adjacent chunks.",
    )
    ask_parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="Maximum number of retrieved chunks to use.",
    )
    ask_parser.add_argument(
        "--min-score",
        type=float,
        default=DEFAULT_MIN_SCORE,
        help="Minimum cosine similarity score for retrieved chunks.",
    )
    ask_parser.add_argument(
        "--provider",
        default=None,
        help="Model provider name from .env, for example DEEPSEEK or KIMI.",
    )
    ask_parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Only print retrieved chunks without calling the chat model.",
    )
    ask_parser.add_argument(
        "--show-chunks",
        action="store_true",
        help="Print retrieved chunk text snippets.",
    )
    ask_parser.add_argument(
        "--trace",
        type=Path,
        default=DEFAULT_TRACE_PATH,
        help="JSONL trace output path.",
    )
    ask_parser.add_argument(
        "--no-trace",
        action="store_true",
        help="Disable JSONL tracing for this run.",
    )
    ask_parser.add_argument(
        "--trace-content",
        action="store_true",
        help="Include retrieved chunk text and generated answer in trace events.",
    )

    eval_parser = subparsers.add_parser("eval", help="Run lightweight retrieval eval cases.")
    eval_parser.add_argument(
        "cases_path",
        nargs="?",
        type=Path,
        default=DEFAULT_EVAL_CASES_PATH,
        help="Path to YAML or JSON eval cases.",
    )
    eval_parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Directory containing source documents.",
    )
    eval_parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Maximum characters per chunk.",
    )
    eval_parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help="Overlapping characters between adjacent chunks.",
    )
    eval_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Default number of retrieved chunks per case.",
    )
    eval_parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Default minimum similarity score per case.",
    )

    return parser


def build_openai_client(provider: str | None = None):
    from openai import OpenAI

    config = load_model_config(provider=provider)
    return OpenAI(api_key=config.api_key, base_url=config.base_url), config


def source_name_for(result: RetrievalResult) -> str:
    return str(result.chunk.metadata.get("source_name") or "unknown")


def source_path_for(result: RetrievalResult) -> str:
    return str(result.chunk.metadata.get("source_path") or "")


def format_retrieval_results(results: list[RetrievalResult], show_chunks: bool = False) -> str:
    if not results:
        return "Retrieved chunks: none"

    lines = ["Retrieved chunks:"]
    for result in results:
        lines.append(
            f"{result.rank}. score={result.score:.4f} "
            f"chunk_id={result.chunk.id} source={source_name_for(result)}"
        )
        if source_path_for(result):
            lines.append(f"   path={source_path_for(result)}")
        if show_chunks:
            snippet = result.chunk.text.replace("\n", " ").strip()
            lines.append(f"   text={snippet[:300]}")

    return "\n".join(lines)


def format_answer_result(result: AnswerResult) -> str:
    lines = [
        "Answer:",
        result.answer,
        "",
        "Citations:",
    ]

    if result.citations:
        lines.extend(f"- {citation}" for citation in result.citations)
    else:
        lines.append("- none")

    if not result.ok:
        lines.extend(
            [
                "",
                f"Warning: answer guard returned error_type={result.error_type}",
            ]
        )

    return "\n".join(lines)


def load_eval_cases(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load retrieval eval cases from YAML or JSON."""

    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
    else:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "Loading YAML eval cases requires PyYAML. "
                "Install with: pip install -e ."
            ) from exc

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    raw = raw or {}
    defaults = raw.get("defaults", {})
    cases = raw.get("cases", [])

    if not isinstance(cases, list):
        raise ValueError("Eval cases file must contain a list field named 'cases'.")

    return defaults, cases


def retrieved_source_names(results: list[RetrievalResult]) -> list[str]:
    """Return source names in retrieval rank order."""

    return [source_name_for(result) for result in results]


def evaluate_retrieval_case(
    case: dict[str, Any],
    index,
    default_top_k: int,
    default_min_score: float,
) -> dict[str, Any]:
    """
    Run one retrieval-only eval case.

    This is a smoke eval, not a semantic answer grader. It checks whether the
    retriever brings the expected document source into the top-k result set.
    """

    case_id = case.get("id")
    query = case.get("query")

    if not case_id or not query:
        raise ValueError("Each eval case must contain 'id' and 'query'.")

    top_k = int(case.get("top_k", default_top_k))
    min_score = float(case.get("min_score", default_min_score))
    expected = case.get("expected", {}) or {}

    results = retrieve(
        query=query,
        index=index,
        top_k=top_k,
        min_score=min_score,
    )
    sources = retrieved_source_names(results)
    top_score = results[0].score if results else None
    top_source = sources[0] if sources else None

    notes: list[str] = []

    for source in expected.get("expected_sources", []):
        if source not in sources:
            notes.append(f"Expected source {source!r} was not retrieved.")

    expected_any = expected.get("expected_sources_any", [])
    if expected_any and not any(source in sources for source in expected_any):
        notes.append(f"None of expected sources were retrieved: {expected_any!r}.")

    if expected.get("top_source") and top_source != expected["top_source"]:
        notes.append(
            f"Expected top source {expected['top_source']!r}, got {top_source!r}."
        )

    min_results = expected.get("min_results")
    if min_results is not None and len(results) < int(min_results):
        notes.append(f"Expected at least {min_results} results, got {len(results)}.")

    min_top_score = expected.get("min_top_score")
    if min_top_score is not None and (top_score is None or top_score < float(min_top_score)):
        notes.append(f"Expected top score >= {min_top_score}, got {top_score}.")

    max_top_score = expected.get("max_top_score")
    if max_top_score is not None and top_score is not None and top_score > float(max_top_score):
        notes.append(f"Expected top score <= {max_top_score}, got {top_score:.4f}.")

    return {
        "case_id": case_id,
        "query": query,
        "success": not notes,
        "notes": notes,
        "sources": sources,
        "top_score": top_score,
        "top_source": top_source,
        "result_count": len(results),
    }


def format_eval_summary(results: list[dict[str, Any]]) -> str:
    """Format eval results for terminal output."""

    passed = sum(1 for result in results if result["success"])
    total = len(results)
    lines = [f"Eval summary: {passed}/{total} passed."]

    for result in results:
        status = "PASS" if result["success"] else "FAIL"
        score = result["top_score"]
        score_text = "none" if score is None else f"{score:.4f}"
        lines.append(
            f"{status} {result['case_id']} "
            f"top_source={result['top_source']} top_score={score_text}"
        )

        if result["sources"]:
            lines.append("  sources=" + ", ".join(result["sources"]))

        for note in result["notes"]:
            lines.append(f"  - {note}")

    return "\n".join(lines)


def ask_command(args: argparse.Namespace) -> int:
    rag_run_id = new_rag_run_id()
    run_start_time = time.perf_counter()
    tracer = None if args.no_trace else JsonlTracer(args.trace)

    emit_trace(
        tracer,
        "rag_run_start",
        rag_run_id=rag_run_id,
        query=args.query,
        data_path=str(args.data),
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        top_k=args.top_k,
        min_score=args.min_score,
        retrieval_only=args.retrieval_only,
    )

    documents = load_documents(args.data)
    emit_trace(
        tracer,
        "document_load_end",
        rag_run_id=rag_run_id,
        document_count=len(documents),
        documents=[
            {
                "id": document.id,
                "source_name": document.source_name,
                "source_path": document.source_path,
                "text_length": len(document.text),
                "metadata": document.metadata,
            }
            for document in documents
        ],
        latency_ms=elapsed_ms(run_start_time),
    )

    index_start_time = time.perf_counter()
    index = build_index_from_documents(
        documents=documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    emit_trace(
        tracer,
        "index_build_end",
        rag_run_id=rag_run_id,
        chunk_count=len(index),
        metadata=index.metadata,
        latency_ms=elapsed_ms(index_start_time),
    )

    retrieval_start_time = time.perf_counter()
    results = retrieve(
        query=args.query,
        index=index,
        top_k=args.top_k,
        min_score=args.min_score,
    )
    emit_trace(
        tracer,
        "retrieval_end",
        rag_run_id=rag_run_id,
        result_count=len(results),
        results=summarize_retrieval_results(
            results,
            include_content=args.trace_content,
        ),
        latency_ms=elapsed_ms(retrieval_start_time),
    )

    print(
        f"Loaded {len(documents)} documents and built an index with "
        f"{len(index)} chunks."
    )
    print(format_retrieval_results(results, show_chunks=args.show_chunks))

    if args.retrieval_only:
        emit_trace(
            tracer,
            "rag_run_end",
            rag_run_id=rag_run_id,
            status="retrieval_only",
            latency_ms=elapsed_ms(run_start_time),
        )
        return 0

    client, config = build_openai_client(provider=args.provider)
    answer_start_time = time.perf_counter()
    answer = answer_query(
        client=client,
        model_id=config.model_id,
        query=args.query,
        results=results,
    )
    emit_trace(
        tracer,
        "answer_end",
        rag_run_id=rag_run_id,
        model_provider=config.provider,
        model_id=config.model_id,
        answer=summarize_answer_result(
            answer,
            include_answer=args.trace_content,
        ),
        latency_ms=elapsed_ms(answer_start_time),
    )

    print()
    print(format_answer_result(answer))

    emit_trace(
        tracer,
        "rag_run_end",
        rag_run_id=rag_run_id,
        status="completed" if answer.ok else "answer_guard_failed",
        error_type=answer.error_type,
        latency_ms=elapsed_ms(run_start_time),
    )

    return 0 if answer.ok else 1


def eval_command(args: argparse.Namespace) -> int:
    defaults, cases = load_eval_cases(args.cases_path)

    documents = load_documents(args.data)
    index = build_index_from_documents(
        documents=documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    default_top_k = int(defaults.get("top_k", args.top_k))
    default_min_score = float(defaults.get("min_score", args.min_score))

    results = [
        evaluate_retrieval_case(
            case=case,
            index=index,
            default_top_k=default_top_k,
            default_min_score=default_min_score,
        )
        for case in cases
    ]

    print(
        f"Loaded {len(documents)} documents and built an index with "
        f"{len(index)} chunks."
    )
    print(format_eval_summary(results))

    return 0 if all(result["success"] for result in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ask":
        return ask_command(args)

    if args.command == "eval":
        return eval_command(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
