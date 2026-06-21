from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .session import AgentSession


Message = dict[str, Any]


def estimate_message_count(messages: list[Message]) -> int:
    return len(messages)


def split_system_messages(messages: list[Message]) -> tuple[list[Message], list[Message]]:
    system_messages: list[Message] = []
    non_system_messages: list[Message] = []

    for message in messages:
        if message.get("role") == "system":
            system_messages.append(message)
        else:
            non_system_messages.append(message)

    return system_messages, non_system_messages


def is_unsafe_context_start(message: Message) -> bool:
    if message.get("role") == "tool":
        return True

    return message.get("role") == "assistant" and bool(message.get("tool_calls"))


def trim_unsafe_prefix(messages: list[Message]) -> list[Message]:
    trimmed = list(messages)

    while trimmed and is_unsafe_context_start(trimmed[0]):
        trimmed = trimmed[1:]

    return trimmed


def trim_message_window(messages: list[Message], max_messages: int) -> list[Message]:
    if max_messages < 1:
        raise ValueError("max_messages must be greater than 0.")

    copied_messages = list(messages)
    if estimate_message_count(copied_messages) <= max_messages:
        return copied_messages

    system_messages, non_system_messages = split_system_messages(copied_messages)
    kept_system_messages = system_messages[-max_messages:]
    remaining_slots = max_messages - len(kept_system_messages)

    if remaining_slots <= 0:
        return kept_system_messages

    recent_messages = non_system_messages[-remaining_slots:]
    recent_messages = trim_unsafe_prefix(recent_messages)

    return kept_system_messages + recent_messages


@dataclass(frozen=True)
class ContextWindow:
    max_messages: int = 20

    def __post_init__(self) -> None:
        if self.max_messages < 1:
            raise ValueError("max_messages must be greater than 0.")

    def build_messages(self, session: AgentSession) -> list[dict[str, Any]]:
        return trim_message_window(
            messages=session.to_model_messages(),
            max_messages=self.max_messages,
        )

    def count_messages(self, session: AgentSession) -> int:
        return estimate_message_count(self.build_messages(session))


def build_context_messages(
    session: AgentSession,
    max_messages: int = 20,
) -> list[Message]:
    return ContextWindow(max_messages=max_messages).build_messages(session)
