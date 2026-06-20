import csv

from agent_harness_mini.evals import (
    EvalCase,
    EvalExpectation,
    EvalResult,
    EvalRunner,
    contains_all,
    contains_any,
    extract_tool_calls,
    load_eval_cases,
    parse_eval_case,
    write_eval_results_csv,
)
from agent_harness_mini.session import AgentRunResult
from agent_harness_mini.tools import ToolRegistry


def test_contains_helpers_are_case_insensitive():
    assert contains_all("Sunny in Hefei", ["sunny", "hefei"]) is True
    assert contains_all("Sunny in Hefei", ["rain"]) is False
    assert contains_any("Sunny in Hefei", ["rain", "sunny"]) is True
    assert contains_any("Sunny in Hefei", ["rain", "snow"]) is False


def test_extract_tool_calls_reads_tool_call_end_events():
    events = [
        {"event": "run_start"},
        {"event": "tool_call_start", "tool_name": "get_weather"},
        {"event": "tool_call_end", "tool_name": "get_weather", "ok": True},
        {"event": "tool_call_end", "tool_name": "get_user_profile", "ok": False},
    ]

    assert extract_tool_calls(events) == ["get_weather", "get_user_profile"]


def test_parse_eval_case_applies_defaults_and_expectations():
    case = parse_eval_case(
        {
            "id": "weather_hefei",
            "input": "Weather in Hefei?",
            "expected": {
                "expected_tools": ["get_weather"],
                "final_contains": ["Hefei"],
            },
        },
        defaults={"max_steps": 5, "system_prompt": "System."},
    )

    assert case.id == "weather_hefei"
    assert case.max_steps == 5
    assert case.system_prompt == "System."
    assert case.expectation.expected_tools == ["get_weather"]
    assert case.expectation.final_contains == ["Hefei"]


def test_load_eval_cases_from_json(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(
        """
        {
          "defaults": {"max_steps": 2},
          "cases": [
            {
              "id": "greeting",
              "input": "Hello",
              "expected": {"status": "completed"}
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    cases = load_eval_cases(path)

    assert len(cases) == 1
    assert cases[0].id == "greeting"
    assert cases[0].max_steps == 2


def test_evaluate_result_passes_when_expectations_match():
    runner = EvalRunner(client=None, model_id="test-model", tool_registry=ToolRegistry())
    case = EvalCase(
        id="weather_hefei",
        input="Weather in Hefei?",
        expectation=EvalExpectation(
            expected_tools=["get_weather"],
            final_contains=["Hefei", "sunny"],
        ),
    )
    run_result = AgentRunResult(
        run_id="run_1",
        session_id="session_1",
        status="completed",
        output="The weather in Hefei is sunny.",
        steps=2,
        latency_ms=100,
    )
    trace_events = [
        {"event": "tool_call_end", "tool_name": "get_weather", "ok": True},
    ]

    result = runner.evaluate_result(case, run_result, trace_events)

    assert result.success is True
    assert result.failure_type is None
    assert result.tool_calls == ["get_weather"]


def test_evaluate_result_fails_for_missing_expected_tool():
    runner = EvalRunner(client=None, model_id="test-model", tool_registry=ToolRegistry())
    case = EvalCase(
        id="weather_hefei",
        input="Weather in Hefei?",
        expectation=EvalExpectation(expected_tools=["get_weather"]),
    )
    run_result = AgentRunResult(
        run_id="run_1",
        session_id="session_1",
        status="completed",
        output="No tool used.",
        steps=1,
        latency_ms=50,
    )

    result = runner.evaluate_result(case, run_result, trace_events=[])

    assert result.success is False
    assert result.failure_type == "tool"
    assert "Expected tool" in result.notes[0]


def test_evaluate_result_fails_for_missing_final_text():
    runner = EvalRunner(client=None, model_id="test-model", tool_registry=ToolRegistry())
    case = EvalCase(
        id="answer_check",
        input="Weather in Hefei?",
        expectation=EvalExpectation(final_contains=["sunny"]),
    )
    run_result = AgentRunResult(
        run_id="run_1",
        session_id="session_1",
        status="completed",
        output="The weather is rainy.",
        steps=1,
        latency_ms=50,
    )

    result = runner.evaluate_result(case, run_result, trace_events=[])

    assert result.success is False
    assert result.failure_type == "answer"


def test_write_eval_results_csv(tmp_path):
    path = tmp_path / "results.csv"
    result = EvalResult(
        case_id="case_1",
        success=True,
        failure_type=None,
        notes=[],
        output="done",
        status="completed",
        tool_calls=["get_weather"],
        latency_ms=10,
        steps=1,
    )

    write_eval_results_csv([result], path)

    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert rows[0]["case_id"] == "case_1"
    assert rows[0]["success"] == "True"
    assert rows[0]["tool_calls"] == "get_weather"
