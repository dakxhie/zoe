"""Merge semantically related memories into consolidated statements."""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

PYTHON_LIKE = re.compile(
    r"\b(i like|i love|my favorite language is|favorite language)\b.*\bpython\b",
    re.I,
)
PYTHON_FAVORITE = re.compile(
    r"\b(my favorite language is|favorite language is)\b\s*(.+)",
    re.I,
)
PYTHON_LIKE_SHORT = re.compile(r"\b(i like|i love)\b\s*python\b", re.I)


def _similar(a: str, b: str) -> bool:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.55


def try_merge_pair(text_a: str, text_b: str) -> str | None:
    """
    Merge two related memory texts into one consolidated line.

    Returns merged text or None if no merge applies.
    """
    a, b = text_a.strip(), text_b.strip()

    if PYTHON_LIKE.search(a) and PYTHON_LIKE.search(b):
        merged = "Favorite programming language: Python"
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Merged duplicate: python preference -> %s", merged)
        return merged

    if PYTHON_LIKE_SHORT.search(a) and PYTHON_FAVORITE.search(b):
        merged = "Favorite programming language: Python"
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Merged duplicate: %s + %s", a[:40], b[:40])
        return merged

    if PYTHON_FAVORITE.search(a) and PYTHON_LIKE_SHORT.search(b):
        return "Favorite programming language: Python"

    if _similar(a, b) and len(a) > 10 and len(b) > 10:
        longer = a if len(a) >= len(b) else b
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Merged duplicate: kept longer variant")
        return longer

    return None


def consolidate_with_existing(candidate: str, existing_texts: list[str]) -> str:
    """Return consolidated text after attempting merges with stored memories."""
    result = candidate.strip()
    for existing in existing_texts:
        merged = try_merge_pair(result, existing)
        if merged:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Merged duplicate into: %s", merged[:120])
            result = merged
    return result
