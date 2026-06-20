import json
from types import SimpleNamespace

from agent_harness_mini.loop import run_agent
from agent_harness_mini.session import AgentSession
from agent_harness_mini.tracing import JsonlTracer, ListTracer
from agent_harness_mini.tools import Tool, ToolRegistry


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        message = self.responses.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self, responses):
        self.completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


def assistant_message(content, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def tool_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def event_names(tracer):
    return [event["event"] for event in tracer.events]


def weather_registry():
    return ToolRegistry(
        [
            Tool(
                name="get_weather",
                description="Get weather.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": ["location"],
                },
                func=lambda location: f"sunny in {location}",
            )
        ]
    )


def test_run_agent_records_basic_events_without_tool_calls():
    client = FakeClient([assistant_message("done")])
    tracer = ListTracer()
    session = AgentSession.create()
    session.add_user_message("hello")

    result = run_agent(
        client=client,
        model_id="test-model",
        session=session,
        tool_registry=ToolRegistry(),
        tracer=tracer,
        run_id="run-basic",
    )

    assert result.status == "completed"
    assert result.output == "done"
    assert result.ok is True
    assert event_names(tracer) == [
        "run_start",
        "step_start",
        "model_call_start",
        "model_call_end",
        "run_end",
    ]
    assert tracer.events[-1]["status"] == "completed"
    assert tracer.events[-1]["output"] == "done"
    assert all(event["run_id"] == "run-basic" for event in tracer.events)
    assert session.messages[-1] == {"role": "assistant", "content": "done"}


def test_run_agent_records_successful_tool_call():
    client = FakeClient(
        [
            assistant_message(
                None,
                [tool_call("get_weather", '{"location": "Hefei"}')],
            ),
            assistant_message("It is sunny."),
        ]
    )
    tracer = ListTracer()
    session = AgentSession.create()
    session.add_user_message("weather?")

    result = run_agent(
        client=client,
        model_id="test-model",
        session=session,
        tool_registry=weather_registry(),
        max_steps=2,
        tracer=tracer,
        run_id="run-tool",
    )

    assert result.status == "completed"
    assert result.output == "It is sunny."
    assert "tool_call_start" in event_names(tracer)
    assert "tool_call_end" in event_names(tracer)

    tool_end = next(event for event in tracer.events if event["event"] == "tool_call_end")
    assert tool_end["ok"] is True
    assert tool_end["tool_name"] == "get_weather"
    assert tool_end["data"] == "sunny in Hefei"

    tool_message = json.loads(session.messages[2]["content"])
    assert tool_message["ok"] is True
    assert tool_message["data"] == "sunny in Hefei"


def test_run_agent_records_invalid_tool_json():
    client = FakeClient(
        [
            assistant_message(
                None,
                [tool_call("get_weather", "{not-json")],
            )
        ]
    )
    tracer = ListTracer()
    session = AgentSession.create()
    session.add_user_message("weather?")

    result = run_agent(
        client=client,
        model_id="test-model",
        session=session,
        tool_registry=weather_registry(),
        max_steps=1,
        tracer=tracer,
        run_id="run-invalid-json",
    )

    assert result.status == "max_steps_exceeded"
    assert result.output == "max_steps_exceeded"
    tool_end = next(event for event in tracer.events if event["event"] == "tool_call_end")
    assert tool_end["ok"] is False
    assert tool_end["error_type"] == "invalid_json"
    assert tracer.events[-1]["status"] == "max_steps_exceeded"


def test_jsonl_tracer_writes_json_lines_and_redacts_secrets(tmp_path):
    path = tmp_path / "trace.jsonl"
    tracer = JsonlTracer(path)

    tracer.record(
        "custom",
        run_id="run-jsonl",
        api_key="secret",
        nested={"access_token": "secret-token", "value": 1},
    )

    line = path.read_text(encoding="utf-8").strip()
    event = json.loads(line)

    assert event["event"] == "custom"
    assert event["api_key"] == "[REDACTED]"
    assert event["nested"]["access_token"] == "[REDACTED]"
    assert event["nested"]["value"] == 1
