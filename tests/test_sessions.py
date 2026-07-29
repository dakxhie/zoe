"""Pytest coverage for conversation session management."""

from __future__ import annotations

from conversation.history import all_sessions, append_message, load_session, messages_since
from conversation.session import create_session, current_session, load_last_session, reset_active_session
from tests.conversation_fixtures import isolated_history  # noqa: F401


def test_create_session_persists_session_id(isolated_history) -> None:
    """Create and persist one session id per chat launch."""
    session_id = create_session()

    assert session_id
    assert current_session() == session_id
    assert load_last_session() is not None
    assert load_last_session().session_id == session_id


def test_multiple_sessions_are_tracked(isolated_history) -> None:
    """Track messages across multiple sessions."""
    first = create_session()
    append_message("user", "first session message")

    reset_active_session()
    second = create_session()
    append_message("user", "second session message")

    assert first != second
    assert all_sessions() == [first, second]
    assert len(load_session(first)) == 1
    assert messages_since(second)[0].content == "second session message"
