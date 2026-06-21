from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_model_config
from .evals import EvalSummary, load_eval_cases, write_eval_results_csv
from .loop import run_agent
from .session import AgentRunResult, AgentSession, build_session
from .tools import build_default_registry
from .tracing import JsonlTracer


DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."
DEFAULT_EVAL_CASE_PROMPT = Path("evals/cases.yaml")
DEFAULT_EVAL_OUTPUT_PATH = Path("evals/results.csv")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-harness-mini",
        description="Run the minimal agent harness from the command line.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one agent task.")
    run_parser.add_argument("prompt", help="User task or message to send to the agent.")
    run_parser.add_argument(
        "--provider",
        default="DEEPSEEK",
        help="Model provider name, for example DEEPSEEK or KIMI.",
    )
    run_parser.add_argument(
        "--system",
        default=DEFAULT_SYSTEM_PROMPT,
        help="System prompt used to initialize the session.",
    )
    run_parser.add_argument(
        "--max-steps",
        type=int,
        default=3,
        help="Maximum agent loop steps.",
    )
    run_parser.add_argument(
        "--trace",
        type=Path,
        default=".traces/run_basic.jsonl",
        help="Optional JSONL trace output path.",
    )
    run_parser.add_argument(
        "--no-trace-content",
        action="store_true",
        help="Record trace metadata without full message/tool content.",
    )

    eval_parser = subparsers.add_parser("eval", help="Run eval cases.")
    eval_parser.add_argument(
        "cases_path",
        nargs="?",
        type=Path,
        default=DEFAULT_EVAL_CASE_PROMPT,
        help="Path to a YAML or JSON eval cases file.",
    )
    eval_parser.add_argument(
        "--cases-path",
        "--cases_path",
        dest="cases_path",
        type=Path,
        default=argparse.SUPPRESS,
        help="Path to a YAML or JSON eval cases file.",
    )
    eval_parser.add_argument(
        "--provider",
        default="DEEPSEEK",
        help="Model provider name, for example DEEPSEEK or KIMI.",
    )
    eval_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_EVAL_OUTPUT_PATH,
        help="CSV file path used to save eval results.",
    )

    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session.")
    chat_parser.add_argument(
        "--provider",
        default="DEEPSEEK",
        help="Model provider name, for example DEEPSEEK or KIMI.",
    )

    chat_parser.add_argument(
        "--system",
        default=DEFAULT_SYSTEM_PROMPT,
        help="System prompt used to initialize the session.",
    )
    chat_parser.add_argument(
        "--max-steps",
        type=int,
        default=3,
        help="Maximum agent loop steps per user turn.",
    )
    chat_parser.add_argument(
        "--trace",
        type=Path,
        default=".traces/chat.jsonl",
        help="Optional JSONL trace output path.",
    )
    chat_parser.add_argument(
        "--no-trace-content",
        action="store_true",
        help="Record trace metadata without full message/tool content.",
    )

    return parser

def build_openai_client(provider: str):
    from openai import OpenAI

    config = load_model_config(provider)
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    return client, config

def run_command(args: argparse.Namespace) -> AgentRunResult:
    from openai import OpenAI

    client, config = build_openai_client(args.provider)
    
    session = build_session(args.system, args.prompt)
    tracer = JsonlTracer(args.trace) if args.trace else None

    return run_agent(
        client=client,
        model_id=config.model_id,
        session=session,
        tool_registry=build_default_registry(),
        max_steps=args.max_steps,
        tracer=tracer,
        trace_content=not args.no_trace_content,
    )


def format_eval_summary(summary: EvalSummary) -> str:
    lines = [
        f"Eval summary: {summary.passed}/{summary.total} passed "
        f"({summary.success_rate:.1%})."
    ]

    for result in summary.results:
        status = "PASS" if result.success else "FAIL"
        lines.append(f"{status} {result.case_id}")

        for note in result.notes:
            lines.append(f"  - {note}")

    return "\n".join(lines)


def eval_command(args: argparse.Namespace) -> int:
    from openai import OpenAI

    from .evals import EvalRunner

    client, config = build_openai_client(args.provider)

    cases = load_eval_cases(args.cases_path)

    

    runner = EvalRunner(
        client=client,
        model_id=config.model_id,
        tool_registry=build_default_registry(),
    )
    summary = runner.run_all(cases)

    if args.output:
        write_eval_results_csv(summary.results, args.output)

    print(format_eval_summary(summary))

    if args.output:
        print(f"Results written to: {args.output}")

    return 0 if summary.failed == 0 else 1

def chat_command(args: argparse.Namespace) -> int:
    from openai import OpenAI

    client, config = build_openai_client(args.provider)

    tool_registry = build_default_registry()
    session = AgentSession.create(args.system)
    tracer = JsonlTracer(args.trace) if args.trace else None

    print("Interactive chat started. Type 'exit' or 'quit' to stop.")

    while True:
        try:
            user_input = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        
        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            return 0
        
        session.add_user_message(user_input)

        result = run_agent(
            client=client,
            model_id=config.model_id,
            session=session,
            tool_registry=tool_registry,
            max_steps=args.max_steps,
            tracer=tracer,
            trace_content=not args.no_trace_content,
        )

        if result.output:
            print(f"\nAssistant> {result.output}")

        if not result.ok:
            print(f"\nRun ended with status: {result.status}")


def main(argv: list[str] | None = None) -> int:

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        result = run_command(args)
        if result.output:
            print(result.output)
        return 0 if result.ok else 1

    if args.command == "eval":
        return eval_command(args)
    
    if args.command == "chat":
        return chat_command(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
