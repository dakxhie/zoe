"""Shared ChromaDB helpers for Zoe AI."""

from __future__ import annotations

import logging
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection

from core.config import ROOT, load_settings

logger = logging.getLogger(__name__)

_client: chromadb.PersistentClient | None = None


class ChromaError(RuntimeError):
    """Raised when shared ChromaDB operations fail."""


def get_chroma_path() -> Path:
    """Return the absolute path to the persistent ChromaDB directory."""
    settings = load_settings()
    db_path = settings.get("MEMORY_DB", "storage/chroma")
    chroma_path = Path(db_path)

    if not chroma_path.is_absolute():
        chroma_path = ROOT / chroma_path

    chroma_path.mkdir(parents=True, exist_ok=True)
    return chroma_path


def get_chroma_client() -> chromadb.PersistentClient:
    """Return a shared persistent ChromaDB client."""
    global _client

    if _client is not None:
        return _client

    chroma_path = get_chroma_path()

    try:
        _client = chromadb.PersistentClient(path=str(chroma_path))
    except Exception as exc:
        raise ChromaError(f"Could not open ChromaDB at '{chroma_path}': {exc}") from exc

    logger.debug("Opened ChromaDB client at %s", chroma_path)
    return _client


def get_collection(name: str) -> Collection:
    """Get or create a named ChromaDB collection."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(name=name)
    logger.debug("Using ChromaDB collection '%s'", name)
    return collection


def existing_ids(collection: Collection) -> set[str]:
    """Return document ids already stored in a collection."""
    if collection.count() == 0:
        return set()

    stored = collection.get(include=[])
    return set(stored["ids"])


def existing_document_texts(collection: Collection) -> set[str]:
    """Return document texts already stored in a collection."""
    if collection.count() == 0:
        return set()

    stored = collection.get(include=["documents"])
    return {document for document in stored["documents"] if document}


def filter_new_ids(item_ids: list[str], known_ids: set[str]) -> list[str]:
    """Return ids that are not already indexed."""
    return [item_id for item_id in item_ids if item_id not in known_ids]
