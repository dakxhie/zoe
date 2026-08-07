"""Shared text normalization helpers for Zoe AI.

Centralizing normalize/match avoids divergent lowercasing and whitespace rules
across routers, memory heuristics, and intent analysis.
"""

from __future__ import annotations


def normalize_text(text: str) -> str:
    """Collapse whitespace and lowercase for case-insensitive phrase matching."""
    return " ".join(text.strip().lower().split())


def matches_any(text: str, phrases: tuple[str, ...]) -> bool:
    """Return True when any phrase is a substring of the (usually normalized) text."""
    return any(phrase in text for phrase in phrases)
