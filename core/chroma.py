"""Shared ChromaDB helpers for Zoe AI."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings

from core.config import ROOT, load_settings

logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

_client: chromadb.PersistentClient | None = None


class ChromaError(RuntimeError):
    """Raised when shared ChromaDB operations fail."""


CHROMA_SQLITE_NAME = "chroma.sqlite3"


def resolve_chroma_path() -> Path:
    """Return the absolute ChromaDB directory path without creating anything."""
    settings = load_settings()
    db_path = settings.get("MEMORY_DB", "storage/chroma")
    chroma_path = Path(db_path)

    if not chroma_path.is_absolute():
        chroma_path = ROOT / chroma_path

    return chroma_path


def get_chroma_path() -> Path:
    """Return the absolute path to the persistent ChromaDB directory."""
    chroma_path = resolve_chroma_path()
    chroma_path.mkdir(parents=True, exist_ok=True)
    return chroma_path


# --- Read-only guard (Phase C) ------------------------------------------------
#
# Read-only callers (``codebase.retriever.search_code``) must never create a
# missing store: no directory, no SQLite database, no collection. These helpers
# only *look*; they open the shared client solely when a store already exists,
# and they never call ``get_or_create_collection``.


def chroma_store_exists(path: Path | None = None) -> bool:
    """True when a persistent Chroma store already exists (directory + SQLite file)."""
    chroma_path = path if path is not None else resolve_chroma_path()
    try:
        return chroma_path.is_dir() and (chroma_path / CHROMA_SQLITE_NAME).is_file()
    except OSError:
        return False


def get_existing_collection(name: str) -> Collection | None:
    """Return an existing collection, or ``None`` when the store or collection is missing.

    Never creates the store directory, the SQLite database or the collection.
    """
    if _client is None and not chroma_store_exists():
        return None
    client = get_chroma_client()
    try:
        names = {_collection_name_from_list_entry(item) for item in client.list_collections()}
    except Exception as exc:
        raise ChromaError(f"Could not list ChromaDB collections: {type(exc).__name__}") from exc
    if name not in names:
        return None
    try:
        return client.get_collection(name=name)
    except Exception as exc:
        raise ChromaError(f"Could not open ChromaDB collection '{name}': {type(exc).__name__}") from exc


def get_chroma_client() -> chromadb.PersistentClient:
    """Return a shared persistent ChromaDB client."""
    global _client

    if _client is not None:
        return _client

    chroma_path = get_chroma_path()

    try:
        _client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False),
        )
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


def _collection_name_from_list_entry(item: Any) -> str:
    """Normalize one entry from ``list_collections()`` to a collection name."""
    if isinstance(item, str):
        return item

    name = getattr(item, "name", None)
    if isinstance(name, str):
        return name

    raise ChromaError(f"Unexpected collection entry from list_collections(): {item!r}")


def list_collection_names() -> list[str]:
    """Return sorted unique collection names from the Chroma client.

    ChromaDB 0.5 and earlier return Collection objects; 0.6+ returns name strings.
    """
    client = get_chroma_client()
    try:
        listed = client.list_collections()
    except Exception as exc:
        raise ChromaError(f"Could not list ChromaDB collections: {exc}") from exc

    names: set[str] = set()
    for item in listed:
        names.add(_collection_name_from_list_entry(item))

    return sorted(names)


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


def collection_count(name: str) -> int:
    """Return the number of documents in a named collection."""
    try:
        return get_collection(name).count()
    except ChromaError as exc:
        logger.debug("Could not count collection '%s': %s", name, exc)
        return 0
