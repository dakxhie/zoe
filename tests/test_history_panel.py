"""History panel helper tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from desktop.history_panel import build_session_rows, delete_session
from desktop.preferences import DesktopPreferences


def test_build_session_rows_uses_preferences_title() -> None:
    """Session rows include renamed titles from desktop preferences."""
    preferences = MagicMock(spec=DesktopPreferences)
    preferences.session_title.return_value = "Planning session"

    message = MagicMock(session="abc", content="Hello there", role="user")
    with patch("desktop.history_panel.all_sessions", return_value=["abc"]), patch(
        "desktop.history_panel.load_session",
        return_value=[message],
    ):
        rows = build_session_rows(preferences)

    assert len(rows) == 1
    assert rows[0].title == "Planning session"
    assert rows[0].preview.startswith("Hello")


def test_delete_session_rewrites_storage() -> None:
    """Deleting a session uses conversation.storage.write_messages."""
    keep = MagicMock(session="keep")
    drop = MagicMock(session="drop")
    with patch("desktop.history_panel.load_all_messages", return_value=[keep, drop]), patch(
        "desktop.history_panel.write_messages"
    ) as mock_write, patch("desktop.history_panel.restore_message_cache") as mock_restore:
        delete_session("drop")

    mock_write.assert_called_once()
    written = mock_write.call_args.args[0]
    assert written == [keep]
    mock_restore.assert_called_once()
