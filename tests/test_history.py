"""Pytest coverage for in-memory conversation history."""

from __future__ import annotations

from memory.history import add_message, clear_history, get_history
from tests.conversation_fixtures import isolated_history  # noqa: F401


def test_fifo_conversation_history(isolated_history) -> None:
    """Keep only the most recent messages in FIFO order."""
    clear_history()

    for index in range(12):
        role = "user" if index % 2 == 0 else "assistant"
        add_message(role, f"message {index}")

    history = get_history(max_messages=10)

    assert len(history) == 10
    assert history[0]["content"] == "message 2"
    assert history[-1]["content"] == "message 11"

    expected_order = [f"message {index}" for index in range(2, 12)]
    actual_order = [message["content"] for message in history]
    assert actual_order == expected_order
