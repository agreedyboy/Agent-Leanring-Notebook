from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .loop import run_agent
from .session import AgentRunResult, AgentSession
from .tools import ToolRegistry
from .tracing import ListTracer


DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


@dataclass(frozen=True)
class EvalExpectation:
    """Declarative checks for one eval case."""

    status: str = "completed"
    expected_tools: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)
    final_contains: list[str] = field(default_factory=list)
    final_contains_any: list[str] = field(default_factory=list)
    max_tool_calls: int | None = None


@dataclass(frozen=True)
class EvalCase:
    """One fixed task used to test agent behavior."""

    id: str
    input: str
    expectation: EvalExpectation
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    max_steps: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalResult:
    """Judged outcome for one eval case."""

    case_id: str
    success: bool
    failure_type: str | None
    notes: list[str]
    output: str | None
    status: str
    tool_calls: list[str]
    latency_ms: int
    steps: int

    def to_dict(self) -> dict[str, Any]:
        """Convert result to a flat row suitable for CSV output."""

        return {
            "case_id": self.case_id,
            "success": self.success,
            "failure_type": self.failure_type,
            "notes": "; ".join(self.notes),
            "output": self.output,
            "status": self.status,
            "tool_calls": ",".join(self.tool_calls),
            "latency_ms": self.latency_ms,
            "steps": self.steps,
        }


@dataclass(frozen=True)
class EvalSummary:
    """Aggregate result for one eval run."""

    total: int
    passed: int
    failed: int
    results: list[EvalResult]

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total


def contains_all(text: str | None, expected: list[str]) -> bool:
    """Return True when every expected string appears in text."""

    if not expected:
        return True
    if not text:
        return False

    lower_text = text.lower()
    return all(item.lower() in lower_text for item in expected)


def contains_any(text: str | None, expected: list[str]) -> bool:
    """Return True when expected is empty or any expected string appears."""

    if not expected:
        return True
    if not text:
        return False

    lower_text = text.lower()
    return any(item.lower() in lower_text for item in expected)


def extract_tool_calls(trace_events: list[dict[str, Any]]) -> list[str]:
    """Extract tool names from tool_call_end trace events."""

    return [
        event["tool_name"]
        for event in trace_events
        if event.get("event") == "tool_call_end" and "tool_name" in event
    ]


def infer_failure_type(notes: list[str]) -> str | None:
    """Infer a coarse failure category from evaluator notes."""

    if not notes:
        return None

    joined = " ".join(notes).lower()

    if "status" in joined:
        return "status"
    if "tool" in joined:
        return "tool"
    if "output" in joined or "text" in joined:
        return "answer"

    return "unknown"


def parse_expectation(raw: dict[str, Any] | None) -> EvalExpectation:
    """Parse the expected section of one raw eval case."""

    raw = raw or {}

    return EvalExpectation(
        status=raw.get("status", "completed"),
        expected_tools=list(raw.get("expected_tools", [])),
        disallowed_tools=list(raw.get("disallowed_tools", [])),
        final_contains=list(raw.get("final_contains", [])),
        final_contains_any=list(raw.get("final_contains_any", [])),
        max_tool_calls=raw.get("max_tool_calls"),
    )


def parse_eval_case(
    raw: dict[str, Any],
    defaults: dict[str, Any] | None = None,
) -> EvalCase:
    """Parse one raw YAML/JSON case into an EvalCase object."""

    defaults = defaults or {}

    return EvalCase(
        id=raw["id"],
        input=raw["input"],
        system_prompt=raw.get(
            "system_prompt",
            defaults.get("system_prompt", DEFAULT_SYSTEM_PROMPT),
        ),
        max_steps=raw.get("max_steps", defaults.get("max_steps", 3)),
        expectation=parse_expectation(raw.get("expected")),
        metadata=raw.get("metadata", {}),
    )


def load_eval_cases(path: str | Path) -> list[EvalCase]:
    """Load eval cases from JSON or YAML."""

    path = Path(path)

    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
    else:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "Loading YAML eval cases requires PyYAML. "
                "Install it or use a .json cases file."
            ) from exc

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    raw = raw or {}
    defaults = raw.get("defaults", {})
    raw_cases = raw.get("cases", [])

    return [parse_eval_case(item, defaults=defaults) for item in raw_cases]


class EvalRunner:
    """Run fixed eval cases and judge agent behavior from output plus trace."""

    def __init__(
        self,
        client: Any,
        model_id: str,
        tool_registry: ToolRegistry,
    ) -> None:
        self.client = client
        self.model_id = model_id
        self.tool_registry = tool_registry

    def run_case(self, case: EvalCase) -> EvalResult:
        """Execute one case through run_agent and evaluate the observed behavior."""

        session = AgentSession.create(case.system_prompt)
        session.add_user_message(case.input)
        tracer = ListTracer()

        try:
            run_result = run_agent(
                client=self.client,
                model_id=self.model_id,
                session=session,
                tool_registry=self.tool_registry,
                max_steps=case.max_steps,
                tracer=tracer,
            )
        except Exception as exc:
            return EvalResult(
                case_id=case.id,
                success=False,
                failure_type="exception",
                notes=[str(exc)],
                output=None,
                status="error",
                tool_calls=[],
                latency_ms=0,
                steps=0,
            )

        return self.evaluate_result(
            case=case,
            run_result=run_result,
            trace_events=tracer.events,
        )

    def evaluate_result(
        self,
        case: EvalCase,
        run_result: AgentRunResult,
        trace_events: list[dict[str, Any]],
    ) -> EvalResult:
        """Compare one observed run against one case's expectations."""

        expectation = case.expectation
        notes: list[str] = []
        tool_calls = extract_tool_calls(trace_events)

        if run_result.status != expectation.status:
            notes.append(
                f"Expected status {expectation.status!r}, got {run_result.status!r}."
            )

        for tool_name in expectation.expected_tools:
            if tool_name not in tool_calls:
                notes.append(f"Expected tool {tool_name!r} was not called.")

        for tool_name in expectation.disallowed_tools:
            if tool_name in tool_calls:
                notes.append(f"Disallowed tool {tool_name!r} was called.")

        if (
            expectation.max_tool_calls is not None
            and len(tool_calls) > expectation.max_tool_calls
        ):
            notes.append(
                f"Expected at most {expectation.max_tool_calls} tool calls, "
                f"got {len(tool_calls)}."
            )

        if not contains_all(run_result.output, expectation.final_contains):
            notes.append(
                f"Final output is missing required text: "
                f"{expectation.final_contains!r}."
            )

        if not contains_any(run_result.output, expectation.final_contains_any):
            notes.append(
                f"Final output does not contain any accepted text: "
                f"{expectation.final_contains_any!r}."
            )

        success = not notes

        return EvalResult(
            case_id=case.id,
            success=success,
            failure_type=infer_failure_type(notes),
            notes=notes,
            output=run_result.output,
            status=run_result.status,
            tool_calls=tool_calls,
            latency_ms=run_result.latency_ms,
            steps=run_result.steps,
        )

    def run_all(self, cases: list[EvalCase]) -> EvalSummary:
        """Run all cases and return aggregate pass/fail counts."""

        results = [self.run_case(case) for case in cases]
        passed = sum(1 for result in results if result.success)

        return EvalSummary(
            total=len(results),
            passed=passed,
            failed=len(results) - passed,
            results=results,
        )


def write_eval_results_csv(results: list[EvalResult], path: str | Path) -> None:
    """Write eval results to a CSV file."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "case_id",
        "success",
        "failure_type",
        "notes",
        "output",
        "status",
        "tool_calls",
        "latency_ms",
        "steps",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            writer.writerow(result.to_dict())
