"""PDF indexing pipeline for ChromaDB."""

from __future__ import annotations

import logging
from typing import Any

from chromadb.api.models.Collection import Collection

from core.chroma import ChromaError, existing_document_texts, existing_ids, get_collection
from core.indexing import prepare_new_chunks
from pdf.chunker import TextChunk, chunk_text
from pdf.loader import PDFLoaderError, load_pdfs
from rag.embedder import embed_texts

COLLECTION_NAME = "zoe_documents"
logger = logging.getLogger(__name__)


class PDFIndexerError(RuntimeError):
    """Raised when PDF indexing cannot proceed due to an unrecoverable error."""


def _get_collection() -> Collection:
    """Get or create the Zoe documents collection."""
    try:
        return get_collection(COLLECTION_NAME)
    except ChromaError as exc:
        raise PDFIndexerError(str(exc)) from exc


def _make_chunk_storage_id(document_id: str, chunk_number: int, _chunk: TextChunk) -> str:
    """Build a stable ChromaDB id for one PDF chunk."""
    return f"{document_id}_chunk_{chunk_number:04d}"


def _prepare_new_chunks(
    document_id: str,
    chunks: list[TextChunk],
    known_ids: set[str],
    known_texts: set[str],
) -> list[tuple[str, TextChunk, int]]:
    """Return chunks that are not already indexed."""
    return prepare_new_chunks(
        chunks,
        lambda chunk_number, chunk: _make_chunk_storage_id(document_id, chunk_number, chunk),
        known_ids,
        known_texts,
        lambda chunk: chunk["text"],
    )


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

    try:
        embeddings = embed_texts(texts)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
    except Exception as exc:
        raise PDFIndexerError(f"Failed to index PDF chunks: {exc}") from exc

    return len(pending_chunks)


def _index_single_pdf(
    collection: Collection,
    document: dict[str, str],
    known_ids: set[str],
    known_texts: set[str],
) -> int:
    """Chunk and index one PDF document."""
    chunks = chunk_text(document["text"])
    pending_chunks = _prepare_new_chunks(document["id"], chunks, known_ids, known_texts)

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
    except PDFLoaderError as exc:
        logger.warning("PDF indexing skipped: %s", exc)
        return 0

    try:
        collection = _get_collection()
    except PDFIndexerError as exc:
        logger.warning("PDF indexing skipped: %s", exc)
        return 0

    known_ids = existing_ids(collection)
    known_texts = existing_document_texts(collection)
    indexed_chunks = 0

    for document in documents:
        try:
            indexed_chunks += _index_single_pdf(
                collection,
                document,
                known_ids,
                known_texts,
            )
        except Exception as exc:
            logger.warning(
                "Skipped PDF '%s' during indexing: %s",
                document["filename"],
                exc,
            )
            continue

    logger.info("Indexed %s PDF chunk(s)", indexed_chunks)
    return indexed_chunks
