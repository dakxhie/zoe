"""PDF document retrieval from ChromaDB."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

import chromadb
from chromadb.api.models.Collection import Collection

from core.config import ROOT, load_settings
from rag.embedder import embed_texts

COLLECTION_NAME = "zoe_documents"


class PDFSearchResult(TypedDict):
    """A PDF chunk returned by semantic search."""

    filename: str
    content: str
    chunk: int


class PDFRetrieverError(RuntimeError):
    """Raised when PDF document search fails."""


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
        raise PDFRetrieverError(
            f"Could not open ChromaDB at '{_get_chroma_path()}': {exc}"
        ) from exc


def _get_collection() -> Collection:
    """Get or create the Zoe documents collection."""
    client = _get_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)


def _format_search_results(results: dict[str, Any]) -> list[PDFSearchResult]:
    """Convert a ChromaDB query response into PDF search results."""
    if not results["ids"] or not results["ids"][0]:
        return []

    formatted: list[PDFSearchResult] = []

    for index, _document_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][index]
        formatted.append(
            {
                "filename": metadata.get("filename", ""),
                "content": results["documents"][0][index],
                "chunk": int(metadata.get("chunk_number", 0)),
            }
        )

    return formatted


def search_documents(query: str, top_k: int = 5) -> list[PDFSearchResult]:
    """Return the most relevant indexed PDF chunks for a query."""
    collection = _get_collection()
    document_count = collection.count()

    if document_count == 0:
        return []

    try:
        query_embedding = embed_texts([query])[0]
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, document_count),
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        raise PDFRetrieverError(f"PDF search failed for query '{query}': {exc}") from exc

    return _format_search_results(results)
