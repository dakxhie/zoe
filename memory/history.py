"""In-memory short-term conversation history for Zoe AI."""

from __future__ import annotations

from typing import TypedDict

MAX_STORED_MESSAGES = 10


class HistoryMessage(TypedDict):
    """One message stored in conversation history."""

    role: str
    content: str


_history: list[HistoryMessage] = []


def add_message(role: str, content: str) -> None:
    """Add one message and keep only the latest stored messages."""
    message: HistoryMessage = {"role": role, "content": content}
    _history.append(message)

    while len(_history) > MAX_STORED_MESSAGES:
        _history.pop(0)


def get_history(max_messages: int = 10) -> list[HistoryMessage]:
    """Return the most recent conversation messages in order."""
    if max_messages <= 0:
        return []

    return _history[-max_messages:].copy()


def clear_history() -> None:
    """Clear all in-memory conversation history."""
    _history.clear()
