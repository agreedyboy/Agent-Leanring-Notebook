"""Small structured tracing helpers for agent runs."""

from __future__ import annotations

import json
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
    """Recorder interface used by the agent loop."""

    def record(self, event: str, **fields: Any) -> None:
        """Record one trace event."""


def new_run_id() -> str:
    """Return a compact id for one agent run."""

    return uuid.uuid4().hex


def utc_timestamp() -> str:
    """Return an ISO 8601 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def make_json_safe(value: Any) -> Any:
    """Convert arbitrary Python values into JSON-serializable values."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]
    return repr(value)


def redact_sensitive(value: Any) -> Any:
    """Redact common secret-bearing keys from nested structures."""

    if isinstance(value, dict):
        redacted = {}
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


def build_event(event: str, **fields: Any) -> TraceEvent:
    """Build one normalized trace event dict."""

    payload = {
        "event": event,
        "timestamp": utc_timestamp(),
        **fields,
    }
    return redact_sensitive(make_json_safe(payload))


def emit_trace(tracer: Tracer | None, event: str, **fields: Any) -> None:
    """Record an event without letting tracing failures affect the agent."""

    if tracer is None:
        return

    try:
        tracer.record(event, **fields)
    except Exception:
        return


class NullTracer:
    """Tracer implementation that intentionally records nothing."""

    def record(self, event: str, **fields: Any) -> None:
        return None


@dataclass
class ListTracer:
    """In-memory tracer useful for tests and notebooks."""

    events: list[TraceEvent] = field(default_factory=list)

    def record(self, event: str, **fields: Any) -> None:
        self.events.append(build_event(event, **fields))


class JsonlTracer:
    """Append trace events to a JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, **fields: Any) -> None:
        payload = build_event(event, **fields)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")
