"""Pytest coverage for conversation history storage."""

from __future__ import annotations

import json

from conversation.history import (
    append_message,
    clear_history,
    history_exists,
    history_size,
    last_messages,
    load_history,
)
from conversation.session import create_session, current_session
from tests.conversation_fixtures import isolated_history  # noqa: F401


def test_append_and_load_history(isolated_history) -> None:
    """Save and reload conversation messages from disk."""
    create_session()
    append_message("user", "My dog is Max.")
    append_message("assistant", "Got it.")

    messages = load_history()

    assert history_exists()
    assert history_size() == 2
    assert messages[0].content == "My dog is Max."
    assert messages[1].role == "assistant"


def test_last_messages_returns_recent_prompt_history(isolated_history) -> None:
    """Return the most recent messages for prompt injection."""
    create_session()
    for index in range(12):
        append_message("user", f"message {index}")

    recent = last_messages(10)

    assert len(recent) == 10
    assert recent[0]["content"] == "message 2"
    assert recent[-1]["content"] == "message 11"


def test_clear_history_removes_files(isolated_history) -> None:
    """Delete persisted history files."""
    create_session()
    append_message("user", "temporary message")

    clear_history()

    assert not history_exists()
    assert history_size() == 0


def test_history_survives_reload(isolated_history, monkeypatch) -> None:
    """Reload history from disk after cache invalidation."""
    create_session()
    append_message("user", "Persistent message")

    import conversation.history as history_module

    history_module._invalidate_cache()
    reloaded = load_history()

    assert reloaded[0].content == "Persistent message"


def test_corrupted_history_line_is_skipped(isolated_history) -> None:
    """Skip unreadable JSONL lines when loading history."""
    isolated_history.mkdir(parents=True, exist_ok=True)
    chat_file = isolated_history / "chat.jsonl"
    chat_file.write_text(
        '{"session":"abc","timestamp":"2026-01-01T00:00:00Z","role":"user","content":"valid"}\n'
        "{not valid json}\n",
        encoding="utf-8",
    )

    import conversation.history as history_module

    history_module._invalidate_cache()
    messages = load_history()

    assert len(messages) == 1
    assert messages[0].content == "valid"


def test_missing_history_folder_is_created_on_append(isolated_history) -> None:
    """Create the history folder automatically."""
    create_session()
    append_message("user", "hello")

    assert (isolated_history / "chat.jsonl").exists()
    payload = json.loads((isolated_history / "chat.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert payload["session"] == current_session()
