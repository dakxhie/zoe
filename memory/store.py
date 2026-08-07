"""Persistent conversation memory storage using ChromaDB."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict

from chromadb.api.models.Collection import Collection

from core.chroma import ChromaError, existing_document_texts, get_collection
from memory.intelligence.memory_types import ScoredMemory
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


def _get_collection() -> Collection:
    """Get or create the Zoe memory collection."""
    try:
        try:
            return get_collection(COLLECTION_NAME)
        except TypeError:
            # Backwards compatibility with tests that patch get_collection() with no args.
            return get_collection()
    except ChromaError as exc:
        raise MemoryStoreError(str(exc)) from exc


def _utc_timestamp() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _build_metadata(created_at: str, scored: ScoredMemory | None = None) -> dict[str, str]:
    """Build metadata for a stored memory document."""
    base: dict[str, str] = {
        "type": MEMORY_TYPE,
        "created_at": created_at,
    }
    if scored is None:
        return base

    base.update(
        {
            "memory_type": scored.memory_type.value,
            "category": scored.category,
            "importance": f"{scored.importance:.4f}",
            "confidence": f"{scored.confidence:.4f}",
            "frequency": str(scored.frequency),
            "last_used": scored.last_used or created_at,
        }
    )
    if scored.expires_at:
        base["expires_at"] = scored.expires_at
    return base


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


def iter_memory_documents() -> list[dict[str, Any]]:
    """Return all memories with ids, text, and metadata for intelligence passes."""
    try:
        collection = _get_collection()
    except MemoryStoreError:
        return []

    if collection.count() == 0:
        return []

    results = collection.get(include=["documents", "metadatas"])
    documents: list[dict[str, Any]] = []
    for index, memory_id in enumerate(results["ids"]):
        documents.append(
            {
                "id": memory_id,
                "text": results["documents"][index],
                "metadata": results["metadatas"][index] or {},
            }
        )
    return documents


def delete_memory_by_id(memory_id: str) -> bool:
    try:
        collection = _get_collection()
        collection.delete(ids=[memory_id])
        return True
    except Exception as exc:
        logger.warning("Failed to delete memory %s: %s", memory_id, exc)
        return False


def save_scored_memory(scored: ScoredMemory) -> bool:
    """Persist a scored memory with full intelligence metadata."""
    memory_text = scored.text.strip()
    if not memory_text:
        return False

    try:
        collection = _get_collection()
    except MemoryStoreError:
        logger.warning("Memory save skipped because ChromaDB is unavailable")
        return False

    if _memory_exists(collection, memory_text):
        logger.debug("Skipped duplicate memory: %s", memory_text[:80])
        return False

    memory_id = str(uuid.uuid4())
    created_at = scored.created or _utc_timestamp()
    metadata = _build_metadata(created_at, scored)

    try:
        embeddings = embed_texts([memory_text])
        collection.add(
            ids=[memory_id],
            documents=[memory_text],
            embeddings=embeddings,
            metadatas=[metadata],
        )
    except Exception as exc:
        raise MemoryStoreError(f"Failed to save memory: {exc}") from exc

    logger.info("Saved conversation memory")
    _notify_memory_saved(memory_text, metadata)
    return True


def _notify_memory_saved(text: str, metadata: dict[str, str]) -> None:
    try:
        from plugins.events import Event, emit
        from plugins.plugin_api import run_memory_hooks

        payload = {"text": text, "metadata": metadata}
        emit(Event.MEMORY_SAVED, payload)
        run_memory_hooks(payload)
    except Exception as exc:
        logger.debug("Memory notify/hooks skipped: %s", exc)


def update_scored_memory(memory_id: str, scored: ScoredMemory) -> bool:
    """Update an existing memory after reinforcement or consolidation."""
    memory_text = scored.text.strip()
    if not memory_text:
        return False

    try:
        collection = _get_collection()
    except MemoryStoreError:
        return False

    created_at = scored.created or _utc_timestamp()
    metadata = _build_metadata(created_at, scored)

    try:
        embeddings = embed_texts([memory_text])
        collection.update(
            ids=[memory_id],
            documents=[memory_text],
            embeddings=embeddings,
            metadatas=[metadata],
        )
    except Exception as exc:
        logger.warning("Memory update via collection.update failed: %s", exc)
        try:
            collection.delete(ids=[memory_id])
            collection.add(
                ids=[memory_id],
                documents=[memory_text],
                embeddings=embeddings,
                metadatas=[metadata],
            )
        except Exception as fallback_exc:
            logger.warning("Memory update fallback failed: %s", fallback_exc)
            return False

    _notify_memory_saved(memory_text, metadata)
    return True


def save_memory(text: str) -> bool:
    """Save a conversation memory through the intelligence pipeline."""
    from memory.intelligence.memory_review import process_memory_candidate

    return process_memory_candidate(text)


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
