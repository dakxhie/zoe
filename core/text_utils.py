"""Shared text normalization helpers for Zoe AI."""

from __future__ import annotations


def normalize_text(text: str) -> str:
    """Normalize user input for case-insensitive matching."""
    return " ".join(text.strip().lower().split())


def matches_any(text: str, phrases: tuple[str, ...]) -> bool:
    """Return True when any phrase appears in the text."""
    return any(phrase in text for phrase in phrases)
