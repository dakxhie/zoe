"""In-memory short-term conversation history for Zoe AI."""

from __future__ import annotations

from typing import TypedDict

from conversation.history import append_message as persist_message
from conversation.history import clear_history as clear_persistent_history
from conversation.history import last_messages

MAX_STORED_MESSAGES = 20


class HistoryMessage(TypedDict):
    """One message stored in conversation history."""

    role: str
    content: str


def add_message(role: str, content: str) -> None:
    """Add one message to persistent conversation history."""
    persist_message(role, content)


def get_history(max_messages: int = MAX_STORED_MESSAGES) -> list[HistoryMessage]:
    """Return the most recent conversation messages in order."""
    return last_messages(max_messages)


def clear_history() -> None:
    """Clear all conversation history."""
    clear_persistent_history()
