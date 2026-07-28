"""Code retrieval from ChromaDB."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

import chromadb
from chromadb.api.models.Collection import Collection

from core.config import ROOT, load_settings
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


def _get_chroma_path() -> Path:
    """Return the absolute path to the persistent ChromaDB directory."""
    settings = load_settings()
    db_path = settings.get("MEMORY_DB", "storage/chroma")
    chroma_path = Path(db_path)

    if not chroma_path.is_absolute():
        chroma_path = ROOT / chroma_path

    chroma_path.mkdir(parents=True, exist_ok=True)
    return chroma_path


def _get_client() -> chromadb.PersistentClient:
    """Create a persistent ChromaDB client."""
    try:
        return chromadb.PersistentClient(path=str(_get_chroma_path()))
    except Exception as exc:
        raise CodeRetrieverError(
            f"Could not open ChromaDB at '{_get_chroma_path()}': {exc}"
        ) from exc


def _get_collection() -> Collection:
    """Get or create the Zoe code collection."""
    client = _get_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)


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
