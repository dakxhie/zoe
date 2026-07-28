"""Disk cache for downloaded webpage text."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from core.config import ROOT

logger = logging.getLogger(__name__)

CACHE_DIR = ROOT / "storage" / "web_cache"


def _ensure_cache_dir() -> Path:
    """Create the cache directory when needed."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def _url_hash(url: str) -> str:
    """Return a stable SHA256 hash for a URL."""
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def _text_path(url: str) -> Path:
    """Return the cache text file path for a URL."""
    return _ensure_cache_dir() / f"{_url_hash(url)}.txt"


def _meta_path(url: str) -> Path:
    """Return the cache metadata file path for a URL."""
    return _ensure_cache_dir() / f"{_url_hash(url)}.meta"


def _utc_timestamp() -> str:
    """Return the current UTC timestamp for cache metadata."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def get_cached_page(url: str) -> str | None:
    """Return cached webpage text when available."""
    text_path = _text_path(url)

    if not text_path.exists():
        return None

    try:
        text = text_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to read cached page for %s: %s", url, exc)
        return None

    if not text.strip():
        return None

    return text


def get_cached_retrieved_at(url: str) -> str | None:
    """Return the cached retrieval timestamp for a URL."""
    meta_path = _meta_path(url)

    if not meta_path.exists():
        return None

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read cache metadata for %s: %s", url, exc)
        return None

    retrieved_at = str(meta.get("retrieved_at", "")).strip()
    return retrieved_at or None


def cache_page(url: str, text: str) -> None:
    """Cache cleaned webpage text and its retrieval timestamp."""
    cleaned = text.strip()
    if not cleaned:
        return

    try:
        _ensure_cache_dir()
        retrieved_at = _utc_timestamp()
        _text_path(url).write_text(cleaned, encoding="utf-8")
        _meta_path(url).write_text(
            json.dumps({"url": url.strip(), "retrieved_at": retrieved_at}),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Failed to cache page %s: %s", url, exc)


def clear_web_cache() -> None:
    """Remove all cached webpage files."""
    if not CACHE_DIR.exists():
        return

    try:
        for path in CACHE_DIR.iterdir():
            if path.is_file():
                path.unlink()
    except OSError as exc:
        logger.warning("Failed to clear web cache: %s", exc)
