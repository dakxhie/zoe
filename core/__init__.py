"""Shared utilities and configuration for Zoe AI."""

from core.chroma import ChromaError, collection_count, get_chroma_client, get_collection
from core.config import ROOT, load_settings
from core.text_utils import matches_any, normalize_text

__all__ = [
    "ChromaError",
    "ROOT",
    "collection_count",
    "get_chroma_client",
    "get_collection",
    "load_settings",
    "matches_any",
    "normalize_text",
]
