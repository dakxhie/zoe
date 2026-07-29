"""Pytest coverage for conversation summarization."""

from __future__ import annotations

from conversation.history import append_message, history_size
from conversation.session import create_session, current_session
from conversation.storage import StoredMessage, SUMMARY_FILE
from conversation.summarizer import (
    load_summary,
    save_summary,
    should_summarize,
    summarize_history,
)
from tests.conversation_fixtures import isolated_history  # noqa: F401


def test_should_summarize_only_after_threshold() -> None:
    """Summarize only when message count exceeds 40."""
    messages = [
        StoredMessage(session="s", timestamp="t", role="user", content=f"msg {index}")
        for index in range(40)
    ]

    assert not should_summarize(messages)

    messages.append(
        StoredMessage(session="s", timestamp="t", role="assistant", content="reply")
    )
    assert should_summarize(messages)


def test_save_and_load_summary(isolated_history) -> None:
    """Persist and reload conversation summaries."""
    save_summary("session-1", "User likes wolves.", ["animals"], ["favorite animal is wolf"])

    summary = load_summary()

    assert summary is not None
    assert summary["summary"] == "User likes wolves."
    assert "wolf" in str(summary["facts"])
    assert SUMMARY_FILE.exists()


def test_summarize_history_uses_local_llm(isolated_history, monkeypatch) -> None:
    """Generate a summary through the local model."""
    create_session()
    for index in range(41):
        append_message("user" if index % 2 == 0 else "assistant", f"message {index}")

    monkeypatch.setattr(
        "conversation.summarizer.load_model",
        lambda: (object(), object()),
    )
    monkeypatch.setattr(
        "conversation.summarizer.generate_text",
        lambda *_args, **_kwargs: (
            "Summary: Long chat about animals.\n"
            "Topics:\n- animals\n"
            "Facts:\n- favorite animal is wolf\n"
            "Tasks:\n- none\n"
            "Preferences:\n- wolves"
        ),
    )

    summary = summarize_history(
        [
            StoredMessage(session=current_session(), timestamp="t", role="user", content=f"message {index}")
            for index in range(41)
        ]
    )

    assert summary is not None
    assert "animals" in str(summary["summary"]).lower()
    assert history_size() == 41
