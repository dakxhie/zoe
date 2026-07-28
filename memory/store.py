"""Persistent conversation memory storage using ChromaDB."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict

from core.chroma import ChromaError, existing_document_texts, get_collection
from memory.detector import should_remember
from rag.embedder import embed_texts

COLLECTION_NAME = "zoe_memory"
MEMORY_TYPE = "conversation_memory"
logger = logging.getLogger(__name__)


class MemoryRecord(TypedDict):
    """A stored conversation memory."""

    id: str
    text: str
    type: str
    created_at: str


class MemoryStoreError(RuntimeError):
    """Raised when memory storage operations fail."""


def _get_collection():
    """Get or create the Zoe memory collection."""
    try:
        return get_collection(COLLECTION_NAME)
    except ChromaError as exc:
        raise MemoryStoreError(str(exc)) from exc


def _utc_timestamp() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _build_metadata(created_at: str) -> dict[str, str]:
    """Build metadata for a stored memory document."""
    return {
        "type": MEMORY_TYPE,
        "created_at": created_at,
    }


def _format_memory_records(results: dict[str, Any]) -> list[MemoryRecord]:
    """Convert a ChromaDB get response into memory records."""
    if not results["ids"]:
        return []

    records: list[MemoryRecord] = []

    for index, memory_id in enumerate(results["ids"]):
        metadata = results["metadatas"][index]
        records.append(
            {
                "id": memory_id,
                "text": results["documents"][index],
                "type": metadata.get("type", MEMORY_TYPE),
                "created_at": metadata.get("created_at", ""),
            }
        )

    records.sort(key=lambda record: record["created_at"])
    return records


def _memory_exists(collection, text: str) -> bool:
    """Return True when the exact memory text is already stored."""
    normalized = text.strip()
    return normalized in existing_document_texts(collection)


def save_memory(text: str) -> bool:
    """Save a conversation memory when it passes the detector rules."""
    if not should_remember(text):
        return False

    try:
        collection = _get_collection()
    except MemoryStoreError:
        logger.warning("Memory save skipped because ChromaDB is unavailable")
        return False

    if _memory_exists(collection, text):
        logger.debug("Skipped duplicate memory: %s", text[:80])
        return False

    memory_id = str(uuid.uuid4())
    created_at = _utc_timestamp()
    metadata = _build_metadata(created_at)

    try:
        embeddings = embed_texts([text])
        collection.add(
            ids=[memory_id],
            documents=[text],
            embeddings=embeddings,
            metadatas=[metadata],
        )
    except Exception as exc:
        raise MemoryStoreError(f"Failed to save memory: {exc}") from exc

    logger.info("Saved conversation memory")
    return True


def list_memories() -> list[MemoryRecord]:
    """Return every stored conversation memory."""
    collection = _get_collection()

    if collection.count() == 0:
        return []

    try:
        results = collection.get(include=["documents", "metadatas"])
    except Exception as exc:
        raise MemoryStoreError(f"Failed to list memories: {exc}") from exc

    return _format_memory_records(results)
