from agent_harness_mini.tools import ToolResult, Tool

def test_tool_converts_to_openai_schema():
    tool = Tool(
        name="get_weather",
        description="Get weather.",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"],
        },
        func=lambda location: f"sunny in {location}",
    )

    schema = tool.to_openai_schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "get_weather"
    assert schema["function"]["parameters"]["required"] == ["location"]


def test_tool_execute_success():
    tool = Tool(
        name="get_weather",
        description="Get weather.",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"],
        },
        func=lambda location: f"sunny in {location}",
    )

    result = tool.execute({"location": "Hefei"})

    assert result.ok is True
    assert result.data == "sunny in Hefei"
    assert result.error_type is None

def test_tool_rejects_missing_required_argument():
    tool = Tool(
        name="get_weather",
        description="Get weather.",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"],
        },
        func=lambda location: f"sunny in {location}",
    )

    result = tool.execute({})

    assert result.ok is False
    assert result.error_type == "invalid_input"
    assert "location" in result.message

def test_tool_rejects_wrong_argument_type():
    tool = Tool(
        name="get_weather",
        description="Get weather.",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"],
        },
        func=lambda location: f"sunny in {location}",
    )

    result = tool.execute({"location": 123})

    assert result.ok is False
    assert result.error_type == "invalid_input"


def test_tool_converts_exception_to_runtime_error():
    def broken_tool(location):
        raise RuntimeError("boom")

    tool = Tool(
        name="get_weather",
        description="Get weather.",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"],
        },
        func=broken_tool,
    )

    result = tool.execute({"location": "Hefei"})

    assert result.ok is False
    assert result.error_type == "runtime_error"
    assert "boom" in result.message

if __name__ == "__main__":
    test_tool_converts_exception_to_runtime_error()
