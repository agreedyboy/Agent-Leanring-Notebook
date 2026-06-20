from agent_harness_mini.session import AgentRunResult, AgentSession


def test_session_create_adds_system_prompt():
    session = AgentSession.create("You are helpful.")

    assert session.session_id
    assert session.messages == [
        {"role": "system", "content": "You are helpful."},
    ]


def test_session_adds_user_assistant_and_tool_messages():
    session = AgentSession.create()

    session.add_user_message("hello")
    session.add_assistant_message({"role": "assistant", "content": "hi"})
    session.add_tool_message(
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "name": "get_weather",
            "content": "{}",
        }
    )

    assert [message["role"] for message in session.messages] == [
        "user",
        "assistant",
        "tool",
    ]


def test_session_snapshot_contains_metadata():
    session = AgentSession.create()
    session.metadata["case_id"] = "demo"

    snapshot = session.snapshot()

    assert snapshot["session_id"] == session.session_id
    assert snapshot["metadata"]["case_id"] == "demo"
    assert "created_at" in snapshot
    assert "updated_at" in snapshot


def test_session_from_messages_copies_outer_message_list():
    messages = [{"role": "user", "content": "hello"}]

    session = AgentSession.from_messages(messages)
    messages.append({"role": "assistant", "content": "external mutation"})

    assert session.messages == [{"role": "user", "content": "hello"}]


def test_to_model_messages_returns_outer_copy():
    session = AgentSession.create()
    session.add_user_message("hello")

    messages = session.to_model_messages()
    messages.append({"role": "assistant", "content": "external mutation"})

    assert session.messages == [{"role": "user", "content": "hello"}]


def test_run_result_ok_reflects_completed_status():
    completed = AgentRunResult(
        run_id="run_1",
        session_id="session_1",
        status="completed",
        output="done",
        steps=1,
        latency_ms=10,
    )
    failed = AgentRunResult(
        run_id="run_2",
        session_id="session_1",
        status="max_steps_exceeded",
        output=None,
        steps=3,
        latency_ms=10,
    )

    assert completed.ok is True
    assert failed.ok is False
