"""Code retrieval from ChromaDB."""

from __future__ import annotations

from typing import Any, TypedDict

from chromadb.api.models.Collection import Collection

from core.chroma import ChromaError, get_existing_collection
from rag.embedder import embed_texts

COLLECTION_NAME = "zoe_code"


class CodeSearchResult(TypedDict):
    """A code chunk returned by semantic search."""

    filename: str
    path: str
    language: str
    content: str


class CodeRetrieverError(RuntimeError):
    """Raised when code search fails."""


def _get_collection() -> Collection | None:
    """Return the existing Zoe code collection, or ``None`` when it does not exist.

    Phase C: search is read-only. A missing Chroma store (or a missing
    ``zoe_code`` collection) is never created here; indexing
    (``codebase.indexer``) remains the only writer.
    """
    try:
        return get_existing_collection(COLLECTION_NAME)
    except ChromaError as exc:
        raise CodeRetrieverError(str(exc)) from exc


def _format_search_results(results: dict[str, Any]) -> list[CodeSearchResult]:
    """Convert a ChromaDB query response into code search results."""
    if not results["ids"] or not results["ids"][0]:
        return []

    formatted: list[CodeSearchResult] = []

    for index, _chunk_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][index]
        formatted.append(
            {
                "filename": metadata.get("filename", ""),
                "path": metadata.get("path", ""),
                "language": metadata.get("language", ""),
                "content": results["documents"][0][index],
            }
        )

    return formatted


def search_code(query: str, top_k: int = 5) -> list[CodeSearchResult]:
    """Return the most relevant indexed code chunks for a query."""
    collection = _get_collection()
    if collection is None:
        return []
    code_count = collection.count()

    if code_count == 0:
        return []

    try:
        query_embedding = embed_texts([query])[0]
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, code_count),
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        raise CodeRetrieverError(f"Code search failed for query '{query}': {exc}") from exc

    return _format_search_results(results)
