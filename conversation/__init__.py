"""Persistent conversation history for Zoe AI."""

from conversation.history import (
    ConversationStatistics,
    append_message,
    all_sessions,
    clear_history,
    conversation_statistics,
    get_summary_text,
    history_exists,
    history_size,
    last_messages,
    load_history,
    load_session,
    messages_since,
    restore_message_cache,
)
from conversation.retriever import (
    HistoryRetrieverError,
    HistorySearchResult,
    retrieve_conversation_context,
    search_history,
)
from conversation.session import create_session, current_session, load_last_session
from conversation.summarizer import load_summary, summarize_history

__all__ = [
    "ConversationStatistics",
    "HistoryRetrieverError",
    "HistorySearchResult",
    "all_sessions",
    "append_message",
    "clear_history",
    "conversation_statistics",
    "create_session",
    "current_session",
    "get_summary_text",
    "history_exists",
    "history_size",
    "last_messages",
    "load_history",
    "load_last_session",
    "load_session",
    "load_summary",
    "messages_since",
    "restore_message_cache",
    "retrieve_conversation_context",
    "search_history",
    "summarize_history",
]
