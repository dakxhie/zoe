"""Code indexing pipeline for ChromaDB."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from code.chunker import CodeChunk, chunk_code
from code.loader import CodeFile, CodeLoaderError, load_code
from core.config import ROOT, load_settings
from rag.embedder import embed_texts

COLLECTION_NAME = "zoe_code"


class CodeIndexerError(RuntimeError):
    """Raised when code indexing cannot proceed due to an unrecoverable error."""


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
        raise CodeIndexerError(
            f"Could not open ChromaDB at '{_get_chroma_path()}': {exc}"
        ) from exc


def _get_collection() -> Collection:
    """Get or create the Zoe code collection."""
    client = _get_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)


def _existing_ids(collection: Collection) -> set[str]:
    """Return chunk ids already stored in the collection."""
    if collection.count() == 0:
        return set()

    stored = collection.get(include=[])
    return set(stored["ids"])


def _make_chunk_storage_id(file_id: str, chunk_number: int) -> str:
    """Build a stable ChromaDB id for one code chunk."""
    safe_file_id = file_id.replace("/", "__")
    return f"{safe_file_id}_chunk_{chunk_number:04d}"


def _prepare_new_chunks(
    file_id: str,
    chunks: list[CodeChunk],
    known_ids: set[str],
) -> list[tuple[str, CodeChunk, int]]:
    """Return chunks that are not already indexed."""
    pending: list[tuple[str, CodeChunk, int]] = []

    for chunk_number, chunk in enumerate(chunks):
        storage_id = _make_chunk_storage_id(file_id, chunk_number)
        if storage_id in known_ids:
            continue
        pending.append((storage_id, chunk, chunk_number))

    return pending


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

    embeddings = embed_texts(texts)
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    return len(pending_chunks)


def _index_single_file(
    collection: Collection,
    code_file: CodeFile,
    known_ids: set[str],
) -> tuple[bool, int]:
    """Chunk and index one code file."""
    chunks = chunk_code(
        code_file["content"],
        code_file["filename"],
        code_file["language"],
    )
    if not chunks:
        return False, 0

    pending_chunks = _prepare_new_chunks(code_file["id"], chunks, known_ids)
    indexed_count = _index_chunk_batch(collection, code_file, pending_chunks)

    for storage_id, _, _ in pending_chunks:
        known_ids.add(storage_id)

    return True, indexed_count


def build_code_index(project_path: str | Path) -> tuple[int, int]:
    """Load, chunk, embed, and store code files. Returns (files, chunks)."""
    try:
        code_files = load_code(project_path)
    except CodeLoaderError:
        return 0, 0

    try:
        collection = _get_collection()
    except CodeIndexerError:
        return 0, 0

    known_ids = _existing_ids(collection)
    indexed_files = 0
    indexed_chunks = 0

    for code_file in code_files:
        try:
            processed, chunk_count = _index_single_file(collection, code_file, known_ids)
        except Exception:
            continue

        if processed:
            indexed_files += 1
        indexed_chunks += chunk_count

    return indexed_files, indexed_chunks
