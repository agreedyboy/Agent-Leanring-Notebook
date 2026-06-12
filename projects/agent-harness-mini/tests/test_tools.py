from types import SimpleNamespace

import pytest

from agent_harness_mini.tools import RetryPolicy, Tool, ToolCallResult, ToolRegistry


def make_weather_tool(**overrides):
    values = {
        "name": "get_weather",
        "description": "Get weather.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
            },
            "required": ["location"],
        },
        "func": lambda location: f"sunny in {location}",
    }
    values.update(overrides)
    return Tool(**values)


def make_tool_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def test_tool_converts_to_openai_schema():
    tool = make_weather_tool()

    schema = tool.to_openai_schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "get_weather"
    assert schema["function"]["parameters"]["required"] == ["location"]


def test_tool_execute_success():
    tool = make_weather_tool()

    result = tool.execute({"location": "Hefei"})

    assert result.ok is True
    assert result.data == "sunny in Hefei"
    assert result.error_type is None
    assert result.attempts == 1


def test_tool_rejects_missing_required_argument():
    tool = make_weather_tool()

    result = tool.execute({})

    assert result.ok is False
    assert result.error_type == "invalid_input"
    assert "location" in result.message


def test_tool_rejects_wrong_argument_type():
    tool = make_weather_tool()

    result = tool.execute({"location": 123})

    assert result.ok is False
    assert result.error_type == "invalid_input"


def test_tool_converts_exception_to_runtime_error():
    def broken_tool(location):
        raise RuntimeError("boom")

    tool = make_weather_tool(func=broken_tool)

    result = tool.execute({"location": "Hefei"})

    assert result.ok is False
    assert result.error_type == "runtime_error"
    assert result.attempts == 1
    assert "boom" in result.message


def test_tool_retries_runtime_error_then_succeeds():
    calls = {"count": 0}

    def unstable_tool(location):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary failure")
        return f"sunny in {location}"

    tool = make_weather_tool(
        func=unstable_tool,
        retry_policy=RetryPolicy(max_retries=1, delay_seconds=0.0),
    )

    result = tool.execute({"location": "Hefei"})

    assert result.ok is True
    assert result.data == "sunny in Hefei"
    assert result.attempts == 2
    assert len(result.metadata["attempts"]) == 2


def test_tool_returns_last_error_after_retries_are_exhausted():
    def broken_tool(location):
        raise RuntimeError("still broken")

    tool = make_weather_tool(
        func=broken_tool,
        retry_policy=RetryPolicy(max_retries=2, delay_seconds=0.0),
    )

    result = tool.execute({"location": "Hefei"})

    assert result.ok is False
    assert result.error_type == "runtime_error"
    assert result.attempts == 3
    assert len(result.metadata["attempts"]) == 3


def test_registry_registers_and_executes_tool():
    registry = ToolRegistry([make_weather_tool()])

    result = registry.execute("get_weather", {"location": "Hefei"})

    assert result.ok is True
    assert result.data == "sunny in Hefei"


def test_registry_rejects_duplicate_tool_name():
    tool = make_weather_tool()
    registry = ToolRegistry([tool])

    with pytest.raises(ValueError):
        registry.register(tool)


def test_registry_returns_unknown_tool_error():
    registry = ToolRegistry()

    result = registry.execute("missing_tool", {})

    assert result.ok is False
    assert result.error_type == "unknown_tool"


def test_registry_execute_tool_call_returns_tool_call_result():
    registry = ToolRegistry([make_weather_tool()])
    tool_call = make_tool_call("get_weather", '{"location": "Hefei"}')

    call_result = registry.execute_tool_call(tool_call)

    assert isinstance(call_result, ToolCallResult)
    assert call_result.tool_call_id == "call_1"
    assert call_result.result.ok is True
    assert call_result.to_tool_message()["tool_call_id"] == "call_1"


def test_registry_execute_tool_call_rejects_invalid_json():
    registry = ToolRegistry([make_weather_tool()])
    tool_call = make_tool_call("get_weather", "{bad-json")

    call_result = registry.execute_tool_call(tool_call)

    assert call_result.tool_call_id == "call_1"
    assert call_result.result.ok is False
    assert call_result.result.error_type == "invalid_json"
