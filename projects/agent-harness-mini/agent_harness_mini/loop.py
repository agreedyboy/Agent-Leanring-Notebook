from __future__ import annotations

import json
import time
from typing import Any

from .tracing import Tracer, emit_trace, new_run_id
from .tools import ToolCallResult, ToolRegistry
from .session import AgentSession, AgentRunResult



def call_model(client: Any, model_id: str, messages: list[dict], tools: list[dict]):
    """Call the chat completion API and return the assistant message."""

    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        tools=tools,
    )
    return response.choices[0].message


def _elapsed_ms(start_time: float) -> int:
    return int((time.perf_counter() - start_time) * 1000)


def _tool_arguments_for_trace(raw_arguments: str | None) -> Any:
    if raw_arguments is None:
        return None

    try:
        return json.loads(raw_arguments)
    except Exception:
        return raw_arguments


def build_tool_message(tool_call_result: ToolCallResult) -> dict[str, Any]:
    """Convert an internal tool result into a role='tool' message."""

    return tool_call_result.to_tool_message()


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
    tool_registry: ToolRegistry,
    session: AgentSession | None = None,
    max_steps: int = 3,
    tracer: Tracer | None = None,
    run_id: str | None = None,
    trace_content: bool = True,
) -> AgentRunResult:
    """
    Run one agent loop.

    The optional tracer records structured events, but tracing failures never
    affect the agent's normal control flow.
    """

    active_run_id = run_id or new_run_id()
    run_start_time = time.perf_counter()

    if session is None:
        session = AgentSession.create({"role": "system", "content": "You are a helpful assistant"})

    emit_trace(
        tracer,
        "run_start",
        run_id=active_run_id,
        session_id = session.session_id,
        model_id=model_id,
        max_steps=max_steps,
        initial_message_count=len(session.to_model_messages()),
        tool_count=len(tool_registry.names()),
    )

    for step in range(max_steps):
        emit_trace(
            tracer,
            "step_start",
            run_id=active_run_id,
            step=step,
            message_count=len(session.to_model_messages()),
        )

        model_start_time = time.perf_counter()
        emit_trace(
            tracer,
            "model_call_start",
            run_id=active_run_id,
            step=step,
            model_id=model_id,
            message_count=len(session.to_model_messages()),

        )

        try:
            assistant_response = call_model(
                client=client,
                model_id=model_id,
                messages=session.to_model_messages(),
                tools=tool_registry.to_openai_tools(),
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
        session.add_assistant_message(assistant_message)

        if not tool_calls:
            emit_trace(
                tracer,
                "run_end",
                run_id=active_run_id,
                session_id = session.session_id,
                status="completed",
                steps=step + 1,
                output=assistant_response.content if trace_content else None,
                latency_ms=_elapsed_ms(run_start_time),
            )
            return AgentRunResult(
                run_id=active_run_id,
                session_id=session.session_id,
                status="completed",
                output=assistant_response.content,
                steps=step + 1,
                latency_ms=_elapsed_ms(run_start_time),
            )

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

            # 执行工具函数
            tool_call_result = tool_registry.execute_tool_call(tool_call=tool_call)
            result = tool_call_result.result

            emit_trace(
                tracer,
                "tool_call_end",
                run_id=active_run_id,
                step=step,
                tool_call_id=tool_call_result.tool_call_id,
                tool_name=result.tool_name,
                ok=result.ok,
                data=result.data if trace_content else None,
                error_type=result.error_type,
                message=result.message,
                latency_ms=result.latency_ms,
                attempts=result.attempts,
                attempt_records=(
                    result.metadata.get("attempts") if trace_content else None
                ),
            )
            session.add_tool_message(build_tool_message(tool_call_result=tool_call_result))

    emit_trace(
        tracer,
        "run_end",
        run_id=active_run_id,
        status="max_steps_exceeded",
        steps=max_steps,
        latency_ms=_elapsed_ms(run_start_time),
    ) 
    return AgentRunResult(
        run_id=active_run_id,
        session_id=session.session_id,
        status="max_steps_exceeded",
        output="max_steps_exceeded",
        steps=max_steps,
        latency_ms=_elapsed_ms(run_start_time),
    )
