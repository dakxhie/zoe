"""Conversation memory retrieval from ChromaDB."""

from __future__ import annotations

from typing import Any, TypedDict

from core.chroma import ChromaError, get_collection
from rag.embedder import embed_texts

COLLECTION_NAME = "zoe_memory"


class MemorySearchResult(TypedDict):
    """A memory returned by semantic search."""

    id: str
    content: str
    created_at: str


class MemoryRetrieverError(RuntimeError):
    """Raised when memory retrieval operations fail."""


def _get_collection():
    """Get or create the Zoe memory collection."""
    try:
        return get_collection(COLLECTION_NAME)
    except ChromaError as exc:
        raise MemoryRetrieverError(str(exc)) from exc


def _format_search_results(results: dict[str, Any]) -> list[MemorySearchResult]:
    """Convert a ChromaDB query response into memory search results."""
    if not results["ids"] or not results["ids"][0]:
        return []

    formatted: list[MemorySearchResult] = []

    for index, memory_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][index]
        formatted.append(
            {
                "id": memory_id,
                "content": results["documents"][0][index],
                "created_at": metadata.get("created_at", ""),
            }
        )

    return formatted


def search_memories(query: str, top_k: int = 3) -> list[MemorySearchResult]:
    """Search stored conversation memories for the most relevant matches."""
    collection = _get_collection()
    memory_count = collection.count()

    if memory_count == 0:
        return []

    try:
        query_embedding = embed_texts([query])[0]
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, memory_count),
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        raise MemoryRetrieverError(
            f"Memory search failed for query '{query}': {exc}"
        ) from exc

    return _format_search_results(results)
