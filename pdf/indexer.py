"""PDF indexing pipeline for ChromaDB."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from core.config import ROOT, load_settings
from pdf.chunker import TextChunk, chunk_text
from pdf.loader import PDFLoaderError, load_pdfs
from rag.embedder import embed_texts

COLLECTION_NAME = "zoe_documents"


class PDFIndexerError(RuntimeError):
    """Raised when PDF indexing cannot proceed due to an unrecoverable error."""


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
        raise PDFIndexerError(
            f"Could not open ChromaDB at '{_get_chroma_path()}': {exc}"
        ) from exc


def _get_collection() -> Collection:
    """Get or create the Zoe documents collection."""
    client = _get_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)


def _existing_ids(collection: Collection) -> set[str]:
    """Return chunk ids already stored in the collection."""
    if collection.count() == 0:
        return set()

    stored = collection.get(include=[])
    return set(stored["ids"])


def _make_chunk_storage_id(document_id: str, chunk_number: int) -> str:
    """Build a stable ChromaDB id for one PDF chunk."""
    return f"{document_id}_chunk_{chunk_number:04d}"


def _prepare_new_chunks(
    document_id: str,
    chunks: list[TextChunk],
    known_ids: set[str],
) -> list[tuple[str, TextChunk, int]]:
    """Return chunks that are not already indexed."""
    pending: list[tuple[str, TextChunk, int]] = []

    for chunk_number, chunk in enumerate(chunks):
        storage_id = _make_chunk_storage_id(document_id, chunk_number)
        if storage_id in known_ids:
            continue
        pending.append((storage_id, chunk, chunk_number))

    return pending


def _index_chunk_batch(
    collection: Collection,
    filename: str,
    document_id: str,
    pending_chunks: list[tuple[str, TextChunk, int]],
) -> int:
    """Embed and store one batch of new PDF chunks."""
    if not pending_chunks:
        return 0

    ids = [storage_id for storage_id, _, _ in pending_chunks]
    texts = [chunk["text"] for _, chunk, _ in pending_chunks]
    metadatas: list[dict[str, Any]] = [
        {
            "filename": filename,
            "document_id": document_id,
            "chunk_number": chunk_number,
        }
        for _, _, chunk_number in pending_chunks
    ]

    embeddings = embed_texts(texts)
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    return len(pending_chunks)


def _index_single_pdf(
    collection: Collection,
    document: dict[str, str],
    known_ids: set[str],
) -> int:
    """Chunk and index one PDF document."""
    chunks = chunk_text(document["text"])
    pending_chunks = _prepare_new_chunks(document["id"], chunks, known_ids)

    indexed_count = _index_chunk_batch(
        collection,
        document["filename"],
        document["id"],
        pending_chunks,
    )

    for storage_id, _, _ in pending_chunks:
        known_ids.add(storage_id)

    return indexed_count


def build_pdf_index() -> int:
    """Load PDFs, chunk them, embed them, and store them in ChromaDB."""
    try:
        documents = load_pdfs()
    except PDFLoaderError:
        return 0

    try:
        collection = _get_collection()
    except PDFIndexerError:
        return 0

    known_ids = _existing_ids(collection)
    indexed_chunks = 0

    for document in documents:
        try:
            indexed_chunks += _index_single_pdf(collection, document, known_ids)
        except Exception:
            continue

    return indexed_chunks
