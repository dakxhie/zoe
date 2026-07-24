"""ChromaDB-backed retrieval for Zoe note documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from core.config import ROOT, load_settings
from rag.embedder import embed_texts
from rag.loader import Document, DocumentLoadError, load_documents

COLLECTION_NAME = "zoe_notes"


class RetrieverError(RuntimeError):
    """Raised when indexing or search operations fail."""


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
        raise RetrieverError(
            f"Could not open ChromaDB at '{_get_chroma_path()}': {exc}"
        ) from exc


def _get_collection() -> Collection:
    """Get or create the Zoe notes collection."""
    client = _get_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)


def _existing_ids(collection: Collection) -> set[str]:
    """Return document ids already stored in the collection."""
    if collection.count() == 0:
        return set()

    stored = collection.get(include=[])
    return set(stored["ids"])


def _filter_new_documents(
    documents: list[Document],
    known_ids: set[str],
) -> list[Document]:
    """Return only documents that are not already indexed."""
    return [document for document in documents if document["id"] not in known_ids]


def _index_documents(collection: Collection, documents: list[Document]) -> int:
    """Insert new documents into ChromaDB and return the number indexed."""
    if not documents:
        return 0

    ids = [document["id"] for document in documents]
    texts = [document["content"] for document in documents]
    filenames = [document["filename"] for document in documents]

    try:
        embeddings = embed_texts(texts)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=[{"filename": filename} for filename in filenames],
        )
    except Exception as exc:
        raise RetrieverError(f"Failed to index documents: {exc}") from exc

    return len(documents)


def build_index() -> int:
    """Load notes, embed them, and store them in ChromaDB without duplicates."""
    try:
        documents = load_documents()
    except DocumentLoadError as exc:
        raise RetrieverError(str(exc)) from exc

    collection = _get_collection()
    new_documents = _filter_new_documents(documents, _existing_ids(collection))
    return _index_documents(collection, new_documents)


def _format_search_results(results: dict[str, Any]) -> list[dict[str, str]]:
    """Convert a Chroma query response into plain document dictionaries."""
    if not results["ids"] or not results["ids"][0]:
        return []

    formatted: list[dict[str, str]] = []

    for index, document_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][index]
        formatted.append(
            {
                "id": document_id,
                "filename": metadata.get("filename", ""),
                "content": results["documents"][0][index],
            }
        )

    return formatted


def search(query: str, top_k: int = 3) -> list[dict[str, str]]:
    """Return the most relevant indexed documents for a query."""
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
        raise RetrieverError(f"Search failed for query '{query}': {exc}") from exc

    return _format_search_results(results)
