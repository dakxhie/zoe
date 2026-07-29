"""Pytest coverage for conversation history CLI commands."""

from __future__ import annotations

from typer.testing import CliRunner

from cli.main import app
from conversation.history import append_message, conversation_statistics
from conversation.session import create_session
from conversation.summarizer import save_summary
from tests.conversation_fixtures import isolated_history  # noqa: F401


runner = CliRunner()


def test_history_prints_recent_messages(isolated_history) -> None:
    """Print the last conversation messages."""
    create_session()
    append_message("user", "Hello there")
    append_message("assistant", "Hi!")

    result = runner.invoke(app, ["history"])

    assert result.exit_code == 0
    assert "User: Hello there" in result.stdout
    assert "Assistant: Hi!" in result.stdout


def test_history_sessions_command(isolated_history) -> None:
    """List stored session ids."""
    session_id = create_session()
    append_message("user", "session message")

    result = runner.invoke(app, ["history", "sessions"])

    assert result.exit_code == 0
    assert session_id in result.stdout


def test_history_summary_command(isolated_history) -> None:
    """Print the stored conversation summary."""
    save_summary("session", "User likes wolves.", ["animals"], ["wolf"])

    result = runner.invoke(app, ["history", "summary"])

    assert result.exit_code == 0
    assert "wolves" in result.stdout


def test_history_clear_command(isolated_history) -> None:
    """Clear persisted conversation history."""
    create_session()
    append_message("user", "temporary")

    result = runner.invoke(app, ["history", "clear"])

    assert result.exit_code == 0
    assert conversation_statistics().messages == 0


def test_history_stats_command(isolated_history) -> None:
    """Print conversation statistics."""
    create_session()
    append_message("user", "stats message")

    result = runner.invoke(app, ["history", "stats"])

    assert result.exit_code == 0
    assert "Messages: 1" in result.stdout
    assert "Sessions: 1" in result.stdout
