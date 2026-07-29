"""Shared fixtures for conversation history tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def isolated_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Route conversation storage to a temporary directory."""
    history_dir = tmp_path / "history"
    monkeypatch.setattr("conversation.storage.HISTORY_DIR", history_dir)
    monkeypatch.setattr("conversation.storage.CHAT_FILE", history_dir / "chat.jsonl")
    monkeypatch.setattr("conversation.storage.SUMMARY_FILE", history_dir / "summary.json")
    monkeypatch.setattr("conversation.session.SESSION_FILE", history_dir / "session.json")

    import conversation.history as history_module
    import conversation.session as session_module

    history_module._invalidate_cache()
    session_module.reset_active_session()
    return history_dir
