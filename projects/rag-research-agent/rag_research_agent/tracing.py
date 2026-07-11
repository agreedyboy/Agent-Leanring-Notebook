from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


SENSITIVE_KEYWORDS = (
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "token",
)


TraceEvent = dict[str, Any]


class Tracer(Protocol):
    """RAG trace recorder 的统一接口。"""

    def record(self, event: str, **fields: Any) -> None:
        """记录一个结构化事件。"""


def new_rag_run_id() -> str:
    """为一次 RAG 查询生成唯一 id，后续接入 Agent tool 时也可以用它关联链路。"""

    return uuid.uuid4().hex


def utc_timestamp() -> str:
    """返回 UTC 时间戳，便于跨机器、跨时区对齐 trace。"""

    return datetime.now(timezone.utc).isoformat()


def elapsed_ms(start_time: float) -> int:
    """根据 perf_counter 的起点计算耗时，单位为毫秒。"""

    return int((time.perf_counter() - start_time) * 1000)


def make_json_safe(value: Any) -> Any:
    """把任意 Python 对象转换为 JSON 可序列化的值。"""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]

    return repr(value)


def redact_sensitive(value: Any) -> Any:
    """递归脱敏，避免 API key、token 等敏感字段进入 trace 文件。"""

    if isinstance(value, dict):
        redacted: dict[str, Any] = {}

        for key, item in value.items():
            key_text = str(key)

            if any(keyword in key_text.lower() for keyword in SENSITIVE_KEYWORDS):
                redacted[key_text] = "[REDACTED]"
            else:
                redacted[key_text] = redact_sensitive(item)

        return redacted

    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]

    return value


def truncate_text(text: str, max_chars: int = 500) -> str:
    """限制长文本长度，避免 trace 文件被 chunk 正文或模型回答快速撑大。"""

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "...[truncated]"


def build_event(event: str, **fields: Any) -> TraceEvent:
    """构造标准 trace event，并做 JSON 安全转换与敏感信息脱敏。"""

    payload = {
        "event": event,
        "timestamp": utc_timestamp(),
        **fields,
    }

    return redact_sensitive(make_json_safe(payload))


def emit_trace(tracer: Tracer | None, event: str, **fields: Any) -> None:
    """
    最佳努力写 trace。

    tracing 是观察能力，不应该影响 RAG 主流程；即使写文件失败，也不打断回答。
    """

    if tracer is None:
        return

    try:
        tracer.record(event, **fields)
    except Exception:
        return


class NullTracer:
    """显式表示不记录 trace 的 recorder。"""

    def record(self, event: str, **fields: Any) -> None:
        return None


@dataclass
class ListTracer:
    """内存 trace recorder，适合后续写单元测试或 notebook 调试。"""

    events: list[TraceEvent] = field(default_factory=list)

    def record(self, event: str, **fields: Any) -> None:
        self.events.append(build_event(event, **fields))


class JsonlTracer:
    """把每个 trace event 追加写入 JSONL 文件。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, **fields: Any) -> None:
        payload = build_event(event, **fields)
        line = json.dumps(payload, ensure_ascii=False) + "\n"

        with self.path.open("a", encoding="utf-8") as file:
            file.write(line)


def summarize_retrieval_results(
    results: list[Any],
    include_content: bool = False,
    max_content_chars: int = 500,
) -> list[dict[str, Any]]:
    """
    把 RetrievalResult 转成适合 trace 的摘要。

    这里故意使用 getattr()，避免 tracing.py import retrieve.py 造成模块耦合。
    """

    summarized: list[dict[str, Any]] = []

    for result in results:
        chunk = getattr(result, "chunk", None)
        metadata = getattr(chunk, "metadata", {}) or {}

        item = {
            "rank": getattr(result, "rank", None),
            # "score": metadata.get("final_score"),
            "score": getattr(result, "score", None),
            "chunk_id": getattr(chunk, "id", None),
            "document_id": getattr(chunk, "document_id", None),
            "source_name": metadata.get("source_name"),
            "source_path": metadata.get("source_path"),
            "start_char": getattr(chunk, "start_char", None),
            "end_char": getattr(chunk, "end_char", None),
            # Hybrid retrieval attaches vector/BM25/final scores here. Keeping
            # the complete small metadata object makes ranking decisions auditable.
            "retrieval_metadata": getattr(result, "metadata", {}) or {},
        }

        if include_content:
            text = getattr(chunk, "text", "") or ""
            item["text"] = truncate_text(text, max_chars=max_content_chars)

        summarized.append(item)

    return summarized


def summarize_answer_result(
    result: Any,
    include_answer: bool = False,
    max_answer_chars: int = 1000,
) -> dict[str, Any]:
    """
    把 AnswerResult 转成适合 trace 的摘要。

    默认不记录完整回答正文；需要排查回答质量时再打开 trace_content。
    """

    answer = getattr(result, "answer", "") or ""

    payload = {
        "ok": getattr(result, "ok", None),
        "error_type": getattr(result, "error_type", None),
        "citations": getattr(result, "citations", []),
        "retrieved_chunk_ids": getattr(result, "retrieved_chunk_ids", []),
        "metadata": getattr(result, "metadata", {}),
    }

    if include_answer:
        payload["answer"] = truncate_text(answer, max_chars=max_answer_chars)

    return payload
