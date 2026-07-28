"""ChromaDB-backed retrieval for Zoe note documents."""

from __future__ import annotations

import logging
from typing import Any

from chromadb.api.models.Collection import Collection

from core.chroma import ChromaError, existing_ids, filter_new_ids, get_collection
from rag.embedder import embed_texts
from rag.loader import Document, DocumentLoadError, load_documents

COLLECTION_NAME = "zoe_notes"
logger = logging.getLogger(__name__)


class RetrieverError(RuntimeError):
    """Raised when indexing or search operations fail."""


def _get_collection() -> Collection:
    """Get or create the Zoe notes collection."""
    try:
        return get_collection(COLLECTION_NAME)
    except ChromaError as exc:
        raise RetrieverError(str(exc)) from exc


def _filter_new_documents(
    documents: list[Document],
    known_ids: set[str],
) -> list[Document]:
    """Return only documents that are not already indexed."""
    allowed_ids = set(filter_new_ids([document["id"] for document in documents], known_ids))
    return [document for document in documents if document["id"] in allowed_ids]


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

    logger.info("Indexed %s note document(s)", len(documents))
    return len(documents)


def build_index() -> int:
    """Load notes, embed them, and store them in ChromaDB without duplicates."""
    try:
        documents = load_documents()
    except DocumentLoadError as exc:
        raise RetrieverError(str(exc)) from exc

    collection = _get_collection()
    new_documents = _filter_new_documents(documents, existing_ids(collection))
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
