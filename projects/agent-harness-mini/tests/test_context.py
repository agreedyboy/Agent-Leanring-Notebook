import pytest

from agent_harness_mini.context import ContextWindow, trim_message_window
from agent_harness_mini.session import AgentSession


def test_context_window_returns_outer_copy_when_under_limit():
    session = AgentSession.create("System prompt.")
    session.add_user_message("Hello")

    messages = ContextWindow(max_messages=3).build_messages(session)

    assert messages == session.messages
    assert messages is not session.messages


def test_context_window_keeps_system_and_recent_messages():
    session = AgentSession.create("System prompt.")

    for index in range(1, 4):
        session.add_user_message(f"user {index}")
        session.add_assistant_message(
            {"role": "assistant", "content": f"assistant {index}"}
        )

    messages = ContextWindow(max_messages=5).build_messages(session)

    assert messages == [
        {"role": "system", "content": "System prompt."},
        {"role": "user", "content": "user 2"},
        {"role": "assistant", "content": "assistant 2"},
        {"role": "user", "content": "user 3"},
        {"role": "assistant", "content": "assistant 3"},
    ]


def test_trim_message_window_does_not_return_all_messages_when_no_slots_remain():
    messages = [
        {"role": "system", "content": "system 1"},
        {"role": "system", "content": "system 2"},
        {"role": "user", "content": "user"},
    ]

    assert trim_message_window(messages, max_messages=2) == [
        {"role": "system", "content": "system 1"},
        {"role": "system", "content": "system 2"},
    ]


def test_trim_message_window_removes_unsafe_tool_prefix():
    system_message = {"role": "system", "content": "System prompt."}
    assistant_tool_call = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "get_weather", "arguments": "{}"},
            }
        ],
    }
    tool_message = {
        "role": "tool",
        "tool_call_id": "call_1",
        "name": "get_weather",
        "content": "{}",
    }
    assistant_after_tool = {"role": "assistant", "content": "It is sunny."}
    user_message = {"role": "user", "content": "Thanks"}

    messages = [
        system_message,
        {"role": "user", "content": "old"},
        assistant_tool_call,
        tool_message,
        assistant_after_tool,
        user_message,
    ]

    assert trim_message_window(messages, max_messages=5) == [
        system_message,
        assistant_after_tool,
        user_message,
    ]


def test_context_window_rejects_invalid_max_messages():
    with pytest.raises(ValueError):
        ContextWindow(max_messages=0)

    with pytest.raises(ValueError):
        trim_message_window([], max_messages=0)
