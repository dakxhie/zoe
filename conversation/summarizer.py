"""Conversation summarization for Zoe AI."""

from __future__ import annotations

import logging
import re

from conversation.storage import (
    SUMMARY_FILE,
    StoredMessage,
    read_json_file,
    utc_timestamp,
    write_json_file,
)

logger = logging.getLogger(__name__)

SUMMARIZE_THRESHOLD = 40


def should_summarize(messages: list[StoredMessage]) -> bool:
    """Return True when the conversation exceeds the summarization threshold."""
    return len(messages) > SUMMARIZE_THRESHOLD


def load_summary() -> dict[str, object] | None:
    """Load the persisted conversation summary."""
    return read_json_file(SUMMARY_FILE)


def save_summary(session_id: str, summary_text: str, topics: list[str], facts: list[str]) -> None:
    """Persist the latest conversation summary."""
    write_json_file(
        SUMMARY_FILE,
        {
            "session": session_id,
            "summary": summary_text,
            "topics": topics,
            "facts": facts,
            "updated": utc_timestamp(),
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

    from brain.generation import generate_text, load_model

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
