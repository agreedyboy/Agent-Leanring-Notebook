from __future__ import annotations

import json
import time
from typing import Any

from .tracing import Tracer, emit_trace, make_json_safe, new_run_id


def call_model(client: Any, model_id: str, messages: list[dict], tools: list[dict]):
    """Call the chat completion API and return the assistant message."""

    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        tools=tools,
    )
    return response.choices[0].message


def parse_tool_arguments(raw_arguments: str) -> dict[str, Any]:
    """Parse tool call arguments from a JSON object string."""

    parsed = json.loads(raw_arguments)
    if not isinstance(parsed, dict):
        raise ValueError("Tool call arguments must be a JSON object.")
    return parsed


def _elapsed_ms(start_time: float) -> int:
    return int((time.perf_counter() - start_time) * 1000)


def _tool_arguments_for_trace(raw_arguments: str | None) -> Any:
    if raw_arguments is None:
        return None

    try:
        return json.loads(raw_arguments)
    except Exception:
        return raw_arguments


def execute_tool_call(tool_call: Any, available_tools: dict[str, Any]) -> dict[str, Any]:
    """Execute one tool call and return a structured tool result."""

    start_time = time.perf_counter()
    tool_call_id = tool_call.id
    function_name = tool_call.function.name

    if function_name not in available_tools:
        return {
            "tool_call_id": tool_call_id,
            "tool_name": function_name,
            "ok": False,
            "data": None,
            "error_type": "unknown_tool",
            "message": f"Tool {function_name!r} is not defined or unavailable.",
            "latency_ms": _elapsed_ms(start_time),
        }

    try:
        function_args = parse_tool_arguments(tool_call.function.arguments)
    except json.JSONDecodeError as exc:
        return {
            "tool_call_id": tool_call_id,
            "tool_name": function_name,
            "ok": False,
            "data": None,
            "error_type": "invalid_json",
            "message": str(exc),
            "latency_ms": _elapsed_ms(start_time),
        }
    except ValueError as exc:
        return {
            "tool_call_id": tool_call_id,
            "tool_name": function_name,
            "ok": False,
            "data": None,
            "error_type": "invalid_arguments",
            "message": str(exc),
            "latency_ms": _elapsed_ms(start_time),
        }

    function_to_call = available_tools[function_name]

    try:
        tool_output = function_to_call(**function_args)
    except Exception as exc:
        return {
            "tool_call_id": tool_call_id,
            "tool_name": function_name,
            "ok": False,
            "data": None,
            "error_type": "runtime_error",
            "message": str(exc),
            "latency_ms": _elapsed_ms(start_time),
        }

    return {
        "tool_call_id": tool_call_id,
        "tool_name": function_name,
        "ok": True,
        "data": tool_output,
        "error_type": None,
        "message": None,
        "latency_ms": _elapsed_ms(start_time),
    }


def build_tool_message(result: dict[str, Any]) -> dict[str, Any]:
    """Convert an internal tool result into a role='tool' message."""

    content = make_json_safe(
        {
            "ok": result["ok"],
            "data": result["data"],
            "error_type": result["error_type"],
            "message": result["message"],
        }
    )
    return {
        "role": "tool",
        "tool_call_id": result["tool_call_id"],
        "name": result["tool_name"],
        "content": json.dumps(content, ensure_ascii=False),
    }


def build_assistant_message(message: Any) -> dict[str, Any]:
    """Convert a model assistant message object into a plain message dict."""
    # print(f"\n\nTest> Message> \t {message}\n\n")
    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        return {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in tool_calls
            ],
        }

    return {
        "role": "assistant",
        "content": message.content,
    }


def run_agent(
    client: Any,
    model_id: str,
    messages: list[dict],
    tools: list[dict],
    available_tools: dict[str, Any],
    max_steps: int = 3,
    tracer: Tracer | None = None,
    run_id: str | None = None,
    trace_content: bool = True,
) -> str | None:
    """
    Run one agent loop.

    The optional tracer records structured events, but tracing failures never
    affect the agent's normal control flow.
    """

    active_run_id = run_id or new_run_id()
    run_start_time = time.perf_counter()

    emit_trace(
        tracer,
        "run_start",
        run_id=active_run_id,
        model_id=model_id,
        max_steps=max_steps,
        initial_message_count=len(messages),
        tool_count=len(tools),
    )

    for step in range(max_steps):
        emit_trace(
            tracer,
            "step_start",
            run_id=active_run_id,
            step=step,
            message_count=len(messages),
        )

        model_start_time = time.perf_counter()
        emit_trace(
            tracer,
            "model_call_start",
            run_id=active_run_id,
            step=step,
            model_id=model_id,
            message_count=len(messages),
            tool_count=len(tools),
        )

        try:
            assistant_response = call_model(
                client=client,
                model_id=model_id,
                messages=messages,
                tools=tools,
            )
        except Exception as exc:
            emit_trace(
                tracer,
                "model_call_end",
                run_id=active_run_id,
                step=step,
                ok=False,
                error_type=type(exc).__name__,
                message=str(exc),
                latency_ms=_elapsed_ms(model_start_time),
            )
            emit_trace(
                tracer,
                "run_end",
                run_id=active_run_id,
                status="error",
                steps=step,
                error_type=type(exc).__name__,
                message=str(exc),
                latency_ms=_elapsed_ms(run_start_time),
            )
            raise

        assistant_message = build_assistant_message(assistant_response)
        tool_calls = getattr(assistant_response, "tool_calls", None) or []

        emit_trace(
            tracer,
            "model_call_end",
            run_id=active_run_id,
            step=step,
            ok=True,
            latency_ms=_elapsed_ms(model_start_time),
            tool_call_count=len(tool_calls),
            assistant_message=assistant_message if trace_content else None,
        )

        messages.append(assistant_message)

        if not tool_calls:
            emit_trace(
                tracer,
                "run_end",
                run_id=active_run_id,
                status="completed",
                steps=step + 1,
                output=assistant_response.content if trace_content else None,
                latency_ms=_elapsed_ms(run_start_time),
            )
            return assistant_response.content

        for tool_call in tool_calls:
            emit_trace(
                tracer,
                "tool_call_start",
                run_id=active_run_id,
                step=step,
                tool_call_id=tool_call.id,
                tool_name=tool_call.function.name,
                arguments=(
                    _tool_arguments_for_trace(tool_call.function.arguments)
                    if trace_content
                    else None
                ),
            )

            result = execute_tool_call(
                tool_call=tool_call,
                available_tools=available_tools,
            )

            emit_trace(
                tracer,
                "tool_call_end",
                run_id=active_run_id,
                step=step,
                tool_call_id=result["tool_call_id"],
                tool_name=result["tool_name"],
                ok=result["ok"],
                data=result["data"] if trace_content else None,
                error_type=result["error_type"],
                message=result["message"],
                latency_ms=result["latency_ms"],
            )

            messages.append(build_tool_message(result=result))

    emit_trace(
        tracer,
        "run_end",
        run_id=active_run_id,
        status="max_steps_exceeded",
        steps=max_steps,
        latency_ms=_elapsed_ms(run_start_time),
    )
    return "max_steps_exceeded"
