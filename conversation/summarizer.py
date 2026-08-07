"""Conversation summarization for Zoe AI."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from conversation.storage import StoredMessage

logger = logging.getLogger(__name__)

SUMMARIZE_THRESHOLD = 40


class _SummaryFileProxy(os.PathLike[str]):
    """
    Live summary-file path for export compatibility.

    Resolves dynamically so monkeypatched temporary directories work, while
    `conversation.summarizer.SUMMARY_FILE` remains a stable imported object
    whose methods (e.g. exists()) reflect the path actually used by
    save_summary / load_summary.
    """

    def _resolve(self) -> Path:
        from conversation import storage

        current = storage.__dict__.get("SUMMARY_FILE")
        # Honor concrete Path monkeypatches on conversation.storage.SUMMARY_FILE.
        if isinstance(current, Path):
            return current
        return storage.HISTORY_DIR / "summary.json"

    def __fspath__(self) -> str:
        return os.fspath(self._resolve())

    def __getattr__(self, name: str):
        return getattr(self._resolve(), name)

    def __str__(self) -> str:
        return str(self._resolve())

    def __repr__(self) -> str:
        return repr(self._resolve())

    def __eq__(self, other: object) -> bool:
        try:
            return self._resolve() == other
        except Exception:
            return NotImplemented


# Stable export: importers hold this proxy; resolution stays dynamic.
SUMMARY_FILE = _SummaryFileProxy()


def _install_summary_file_export() -> None:
    """Share the live proxy via conversation.storage when still a static Path."""
    from conversation import storage

    current = storage.__dict__.get("SUMMARY_FILE")
    if isinstance(current, Path) or current is None:
        storage.SUMMARY_FILE = SUMMARY_FILE


_install_summary_file_export()


def load_model():
    """Load the chat model (wrapper kept for callers/tests that patch this module)."""
    from brain.generation import load_model as _load_model

    return _load_model()


def generate_text(*args, **kwargs):
    """Generate text (wrapper kept for callers/tests that patch this module)."""
    from brain.generation import generate_text as _generate_text

    return _generate_text(*args, **kwargs)


def should_summarize(messages: list[StoredMessage]) -> bool:
    """Return True when the conversation exceeds the summarization threshold."""
    return len(messages) > SUMMARIZE_THRESHOLD


def load_summary() -> dict[str, object] | None:
    """Load the persisted conversation summary."""
    from conversation import storage

    return storage.read_json_file(storage.SUMMARY_FILE)


def save_summary(session_id: str, summary_text: str, topics: list[str], facts: list[str]) -> None:
    """Persist the latest conversation summary."""
    from conversation import storage

    storage.write_json_file(
        storage.SUMMARY_FILE,
        {
            "session": session_id,
            "summary": summary_text,
            "topics": topics,
            "facts": facts,
            "updated": storage.utc_timestamp(),
        },
    )


def _format_messages_for_summary(messages: list[StoredMessage]) -> str:
    """Format messages for the summarization prompt."""
    lines: list[str] = []
    for message in messages[-120:]:
        lines.append(f"{message.role}: {message.content}")
    return "\n".join(lines)


def _parse_summary_sections(text: str) -> tuple[str, list[str], list[str], list[str]]:
    """Parse structured sections from a model summary response."""
    summary = text.strip()
    topics: list[str] = []
    facts: list[str] = []
    tasks: list[str] = []

    sections = {
        "topics": topics,
        "facts": facts,
        "tasks": tasks,
    }

    current: list[str] | None = None
    for line in text.splitlines():
        normalized = line.strip().lower()
        if normalized.startswith("summary:"):
            summary = line.split(":", 1)[1].strip()
            current = None
            continue
        if normalized.startswith("topics:"):
            current = topics
            continue
        if normalized.startswith("facts:"):
            current = facts
            continue
        if normalized.startswith("tasks:"):
            current = tasks
            continue
        if normalized.startswith("preferences:"):
            current = facts
            continue
        if current is not None and line.strip():
            cleaned = re.sub(r"^[-*]\s*", "", line.strip())
            if cleaned:
                current.append(cleaned)

    if not summary:
        summary = text.strip()

    return summary, topics, facts, tasks


def summarize_history(messages: list[StoredMessage]) -> dict[str, object] | None:
    """Summarize a long conversation using the local LLM."""
    if not should_summarize(messages):
        return None

    transcript = _format_messages_for_summary(messages)
    prompt_messages = [
        {
            "role": "system",
            "content": (
                "You summarize conversations for a personal assistant.\n"
                "Return these sections:\n"
                "Summary:\n"
                "Topics:\n"
                "Facts:\n"
                "Tasks:\n"
                "Preferences:\n"
                "Use concise bullet points where appropriate."
            ),
        },
        {
            "role": "user",
            "content": f"Summarize this conversation:\n\n{transcript}",
        },
    ]

    try:
        tokenizer, model = load_model()
        summary_text = generate_text(tokenizer, model, prompt_messages, max_new_tokens=256)
    except Exception as exc:
        logger.warning("Conversation summarization failed: %s", exc)
        return None

    summary, topics, facts, _tasks = _parse_summary_sections(summary_text)
    session_id = messages[-1].session if messages else ""
    save_summary(session_id, summary, topics, facts)
    return load_summary()


def summary_as_text(summary: dict[str, object] | None) -> str:
    """Format a stored summary dictionary as prompt text."""
    if not summary:
        return ""

    parts: list[str] = []
    main = str(summary.get("summary", "")).strip()
    if main:
        parts.append(main)

    topics = summary.get("topics")
    if isinstance(topics, list) and topics:
        parts.append("Topics: " + "; ".join(str(item) for item in topics))

    facts = summary.get("facts")
    if isinstance(facts, list) and facts:
        parts.append("Important facts: " + "; ".join(str(item) for item in facts))

    return "\n".join(parts).strip()
