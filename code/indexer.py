"""Code indexing pipeline for ChromaDB."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from chromadb.api.models.Collection import Collection

from code.chunker import CodeChunk, chunk_code
from code.loader import CodeFile, CodeLoaderError, load_code
from core.chroma import ChromaError, existing_document_texts, existing_ids, get_collection
from core.indexing import prepare_new_chunks
from rag.embedder import embed_texts

COLLECTION_NAME = "zoe_code"
logger = logging.getLogger(__name__)


class CodeIndexerError(RuntimeError):
    """Raised when code indexing cannot proceed due to an unrecoverable error."""


def _get_collection() -> Collection:
    """Get or create the Zoe code collection."""
    try:
        return get_collection(COLLECTION_NAME)
    except ChromaError as exc:
        raise CodeIndexerError(str(exc)) from exc


def _make_chunk_storage_id(file_id: str, chunk_number: int, _chunk: CodeChunk) -> str:
    """Build a stable ChromaDB id for one code chunk."""
    safe_file_id = file_id.replace("/", "__")
    return f"{safe_file_id}_chunk_{chunk_number:04d}"


def _prepare_new_chunks(
    file_id: str,
    chunks: list[CodeChunk],
    known_ids: set[str],
    known_texts: set[str],
) -> list[tuple[str, CodeChunk, int]]:
    """Return chunks that are not already indexed."""
    return prepare_new_chunks(
        chunks,
        lambda chunk_number, chunk: _make_chunk_storage_id(file_id, chunk_number, chunk),
        known_ids,
        known_texts,
        lambda chunk: chunk["text"],
    )


def _index_chunk_batch(
    collection: Collection,
    code_file: CodeFile,
    pending_chunks: list[tuple[str, CodeChunk, int]],
) -> int:
    """Embed and store one batch of new code chunks."""
    if not pending_chunks:
        return 0

    ids = [storage_id for storage_id, _, _ in pending_chunks]
    texts = [chunk["text"] for _, chunk, _ in pending_chunks]
    metadatas: list[dict[str, Any]] = [
        {
            "filename": code_file["filename"],
            "path": code_file["path"],
            "language": chunk["language"],
            "chunk_number": chunk_number,
        }
        for _, chunk, chunk_number in pending_chunks
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
        raise CodeIndexerError(f"Failed to index code chunks: {exc}") from exc

    return len(pending_chunks)


def _index_single_file(
    collection: Collection,
    code_file: CodeFile,
    known_ids: set[str],
    known_texts: set[str],
) -> tuple[bool, int]:
    """Chunk and index one code file."""
    chunks = chunk_code(
        code_file["content"],
        code_file["filename"],
        code_file["language"],
    )
    if not chunks:
        return False, 0

    pending_chunks = _prepare_new_chunks(code_file["id"], chunks, known_ids, known_texts)
    indexed_count = _index_chunk_batch(collection, code_file, pending_chunks)

    for storage_id, _, _ in pending_chunks:
        known_ids.add(storage_id)

    return True, indexed_count


def build_code_index(project_path: str | Path) -> tuple[int, int]:
    """Load, chunk, embed, and store code files. Returns (files, chunks)."""
    try:
        code_files = load_code(project_path)
    except CodeLoaderError as exc:
        logger.warning("Code indexing skipped: %s", exc)
        return 0, 0

    try:
        collection = _get_collection()
    except CodeIndexerError as exc:
        logger.warning("Code indexing skipped: %s", exc)
        return 0, 0

    known_ids = existing_ids(collection)
    known_texts = existing_document_texts(collection)
    indexed_files = 0
    indexed_chunks = 0

    for code_file in code_files:
        try:
            processed, chunk_count = _index_single_file(
                collection,
                code_file,
                known_ids,
                known_texts,
            )
        except Exception as exc:
            logger.warning(
                "Skipped code file '%s' during indexing: %s",
                code_file["path"],
                exc,
            )
            continue

        if processed:
            indexed_files += 1
        indexed_chunks += chunk_count

    logger.info("Indexed %s code file(s) and %s chunk(s)", indexed_files, indexed_chunks)
    return indexed_files, indexed_chunks
