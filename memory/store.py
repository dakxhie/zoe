"""Persistent conversation memory storage using ChromaDB."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

import chromadb
from chromadb.api.models.Collection import Collection

from core.config import ROOT, load_settings
from memory.detector import should_remember
from rag.embedder import embed_texts

COLLECTION_NAME = "zoe_memory"
MEMORY_TYPE = "conversation_memory"


class MemoryRecord(TypedDict):
    """A stored conversation memory."""

    id: str
    text: str
    type: str
    created_at: str


class MemoryStoreError(RuntimeError):
    """Raised when memory storage operations fail."""


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
        raise MemoryStoreError(
            f"Could not open ChromaDB at '{_get_chroma_path()}': {exc}"
        ) from exc


def _get_collection() -> Collection:
    """Get or create the Zoe memory collection."""
    client = _get_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)


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


def save_memory(text: str) -> bool:
    """Save a conversation memory when it passes the detector rules."""
    if not should_remember(text):
        return False

    memory_id = str(uuid.uuid4())
    created_at = _utc_timestamp()
    metadata = _build_metadata(created_at)

    try:
        collection = _get_collection()
        embeddings = embed_texts([text])
        collection.add(
            ids=[memory_id],
            documents=[text],
            embeddings=embeddings,
            metadatas=[metadata],
        )
    except Exception as exc:
        raise MemoryStoreError(f"Failed to save memory: {exc}") from exc

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
