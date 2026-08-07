"""Persistent conversation history API for Zoe AI."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from conversation.retriever import clear_history_index, index_message, search_history
from conversation.session import current_session, reset_active_session
from conversation.storage import (
    StoredMessage,
    chat_file_exists,
    delete_history_files,
    load_all_messages,
    utc_timestamp,
)
from conversation.summarizer import load_summary, should_summarize, summarize_history

logger = logging.getLogger(__name__)

PROMPT_MESSAGE_LIMIT = 20
_recent_cache: list[StoredMessage] | None = None


@dataclass(frozen=True)
class ConversationStatistics:
    """Summary statistics for persisted conversation history."""

    messages: int
    sessions: int
    token_estimate: int
    summary_size: int
    database_size: int


def _invalidate_cache() -> None:
    """Clear the in-memory recent history cache."""
    global _recent_cache
    _recent_cache = None


def _cache_messages(messages: list[StoredMessage]) -> list[StoredMessage]:
    """Store messages in the recent cache."""
    global _recent_cache
    _recent_cache = messages.copy()
    return _recent_cache


def _cached_or_load_messages() -> list[StoredMessage]:
    """Return cached messages or load them from disk once."""
    global _recent_cache
    if _recent_cache is None:
        _recent_cache = load_all_messages()
    return _recent_cache


def history_exists() -> bool:
    """Return True when persisted conversation history is available."""
    return chat_file_exists()


def append_message(role: str, text: str) -> StoredMessage:
    """Append one conversation message to disk and the history index."""
    from conversation.storage import append_jsonl

    message = StoredMessage(
        session=current_session(),
        timestamp=utc_timestamp(),
        role=role.strip(),
        content=text.strip(),
        id=str(uuid.uuid4()),
    )
    append_jsonl(message)

    global _recent_cache
    if _recent_cache is None:
        _cache_messages(load_all_messages())
    else:
        updated = _recent_cache.copy()
        updated.append(message)
        _cache_messages(updated)

    try:
        index_message(message)
    except Exception as exc:
        logger.warning("Conversation indexing failed: %s", exc)

    if should_summarize(_cached_or_load_messages()):
        try:
            summarize_history(_cached_or_load_messages())
        except Exception as exc:
            logger.warning("Conversation summarization skipped: %s", exc)

    return message


def load_history() -> list[StoredMessage]:
    """Load the full conversation history."""
    return _cached_or_load_messages().copy()


def clear_history() -> None:
    """Delete persisted conversation history and indexes."""
    delete_history_files()
    clear_history_index()
    reset_active_session()
    _invalidate_cache()


def last_messages(n: int) -> list[dict[str, str]]:
    """Return the most recent messages formatted for chat prompts."""
    if n <= 0:
        return []

    messages = _cached_or_load_messages()[-n:]
    return [{"role": message.role, "content": message.content} for message in messages]


def messages_since(session_id: str) -> list[StoredMessage]:
    """Return messages belonging to one session."""
    return [message for message in _cached_or_load_messages() if message.session == session_id]


def all_sessions() -> list[str]:
    """Return all session ids found in the history file."""
    sessions: list[str] = []
    seen: set[str] = set()
    for message in _cached_or_load_messages():
        if message.session in seen:
            continue
        seen.add(message.session)
        sessions.append(message.session)
    return sessions


def load_session(session_id: str) -> list[StoredMessage]:
    """Return all messages for a specific session id."""
    return messages_since(session_id)


def history_size() -> int:
    """Return the number of stored conversation messages."""
    return len(_cached_or_load_messages())


def conversation_statistics() -> ConversationStatistics:
    """Return aggregate statistics for conversation history."""
    from conversation import storage

    messages = _cached_or_load_messages()
    content_chars = sum(len(message.content) for message in messages)
    summary_payload = load_summary() or {}
    summary_text = str(summary_payload.get("summary", ""))
    database_size = storage.file_size_bytes(storage.CHAT_FILE) + storage.file_size_bytes(
        storage.SUMMARY_FILE
    )

    return ConversationStatistics(
        messages=len(messages),
        sessions=len(all_sessions()),
        token_estimate=max(1, content_chars // 4),
        summary_size=len(summary_text),
        database_size=database_size,
    )


def get_summary_text() -> str:
    """Return the latest summary formatted for prompt injection."""
    from conversation.summarizer import summary_as_text

    return summary_as_text(load_summary())


def restore_message_cache() -> None:
    """Warm the recent history cache from disk."""
    _cache_messages(load_all_messages())
