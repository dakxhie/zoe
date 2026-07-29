"""Chroma-backed conversation history retrieval for Zoe AI."""

from __future__ import annotations

import logging
import uuid
from typing import Any, TypedDict

from chromadb.api.models.Collection import Collection

from conversation.storage import StoredMessage
from core.chroma import ChromaError, get_collection
from rag.embedder import embed_texts

logger = logging.getLogger(__name__)

COLLECTION_NAME = "zoe_history"
MAX_CONTEXT_WORDS = 2000
SEARCH_TOP_K = 5
RECENT_TURN_LIMIT = 6


class HistorySearchResult(TypedDict):
    """One conversation message returned by semantic search."""

    id: str
    session: str
    role: str
    content: str
    timestamp: str
    score: float


class HistoryRetrieverError(RuntimeError):
    """Raised when conversation retrieval operations fail."""


def _get_collection() -> Collection:
    """Get or create the conversation history collection."""
    try:
        return get_collection(COLLECTION_NAME)
    except ChromaError as exc:
        raise HistoryRetrieverError(str(exc)) from exc


def _message_document(message: StoredMessage) -> str:
    """Build the searchable document text for one message."""
    return f"{message.role}: {message.content}"


def index_message(message: StoredMessage) -> str:
    """Embed and store one conversation message in ChromaDB."""
    message_id = message.id or str(uuid.uuid4())
    collection = _get_collection()

    try:
        embedding = embed_texts([_message_document(message)])[0]
        collection.add(
            ids=[message_id],
            documents=[_message_document(message)],
            embeddings=[embedding],
            metadatas=[
                {
                    "session": message.session,
                    "role": message.role,
                    "timestamp": message.timestamp,
                }
            ],
        )
    except Exception as exc:
        raise HistoryRetrieverError(f"Failed to index conversation message: {exc}") from exc

    return message_id


def clear_history_index() -> None:
    """Delete every document in the conversation history collection."""
    try:
        collection = _get_collection()
    except HistoryRetrieverError:
        return

    if collection.count() == 0:
        return

    stored = collection.get(include=[])
    ids = stored.get("ids") or []
    if ids:
        collection.delete(ids=ids)


def _format_search_results(results: dict[str, Any]) -> list[HistorySearchResult]:
    """Convert a Chroma query response into history search results."""
    if not results["ids"] or not results["ids"][0]:
        return []

    formatted: list[HistorySearchResult] = []
    distances = results.get("distances", [[0.0]])[0]

    for index, message_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][index]
        distance = distances[index] if index < len(distances) else 0.0
        formatted.append(
            {
                "id": message_id,
                "session": str(metadata.get("session", "")),
                "role": str(metadata.get("role", "")),
                "content": results["documents"][0][index],
                "timestamp": str(metadata.get("timestamp", "")),
                "score": float(max(0.0, 1.0 - distance)),
            }
        )

    formatted.sort(key=lambda item: item["score"], reverse=True)
    return formatted


def search_history(query: str, top_k: int = SEARCH_TOP_K) -> list[HistorySearchResult]:
    """Search prior conversation turns by semantic similarity."""
    collection = _get_collection()
    if collection.count() == 0:
        return []

    try:
        query_embedding = embed_texts([query])[0]
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        raise HistoryRetrieverError(f"Conversation search failed: {exc}") from exc

    return _format_search_results(results)


def _truncate_words(text: str, max_words: int) -> str:
    """Truncate text to a maximum number of words."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip() + "..."


def _format_turn(result: HistorySearchResult) -> str:
    """Format one retrieved turn for prompt injection."""
    role = result["role"].capitalize()
    content = result["content"]
    if content.lower().startswith(f"{result['role']}:"):
        content = content.split(":", 1)[1].strip()
    return f"{role}: {content}"


def retrieve_conversation_context(
    query: str,
    *,
    summary_text: str = "",
    recent_messages: list[StoredMessage] | None = None,
) -> str:
    """Build deduplicated conversation context from summary, search, and recents."""
    sections: list[str] = []
    seen: set[str] = set()

    if summary_text.strip():
        sections.append("Conversation Summary:\n" + summary_text.strip())

    relevant = search_history(query)
    relevant_lines: list[str] = []
    for result in relevant:
        line = _format_turn(result)
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        relevant_lines.append(line)
    if relevant_lines:
        sections.append("Relevant Conversation:\n" + "\n".join(relevant_lines))

    if recent_messages:
        recent_lines: list[str] = []
        for message in recent_messages[-RECENT_TURN_LIMIT:]:
            line = f"{message.role.capitalize()}: {message.content}"
            key = line.lower()
            if key in seen:
                continue
            seen.add(key)
            recent_lines.append(line)
        if recent_lines:
            sections.append("Recent Conversation:\n" + "\n".join(recent_lines))

    if not sections:
        return ""

    return _truncate_words("\n\n".join(sections), MAX_CONTEXT_WORDS)
