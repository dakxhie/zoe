"""Base importance rules by memory type and content."""

from __future__ import annotations

import re

from core.text_utils import matches_any, normalize_text
from memory.intelligence.memory_types import MemoryType

IDENTITY_PHRASES: tuple[str, ...] = (
    "my name is",
    "i am ",
    "call me ",
)

PROJECT_PHRASES: tuple[str, ...] = (
    "i am building",
    "i work on",
    "my project",
    "building ",
    "working on",
)

PREFERENCE_PHRASES: tuple[str, ...] = (
    "my favorite",
    "i prefer",
    "i like",
    "i love",
    "i hate",
    "dark theme",
    "light theme",
)

PROCEDURAL_PHRASES: tuple[str, ...] = (
    "i usually",
    "i always",
    "my workflow",
    "preferred ide",
    "favorite language",
    "favorite editor",
)

EPISODE_PHRASES: tuple[str, ...] = (
    "yesterday",
    "last week",
    "today i",
    "we analyzed",
    "i analyzed",
    "remember when",
)

LOCATION_PATTERN = re.compile(r"\b(i live in|i'm from|from)\b")

BASE_IMPORTANCE: dict[MemoryType, float] = {
    MemoryType.IDENTITY: 0.95,
    MemoryType.PROJECT: 0.9,
    MemoryType.PREFERENCE: 0.8,
    MemoryType.PROCEDURAL: 0.75,
    MemoryType.SEMANTIC: 0.65,
    MemoryType.EPISODE: 0.55,
    MemoryType.TEMPORARY: 0.25,
}


def classify_memory_type(text: str) -> MemoryType:
    """Infer memory type from natural language."""
    normalized = normalize_text(text)

    if matches_any(normalized, PROJECT_PHRASES):
        return MemoryType.PROJECT
    if matches_any(normalized, PREFERENCE_PHRASES):
        return MemoryType.PREFERENCE
    if matches_any(normalized, IDENTITY_PHRASES) or "my name" in normalized:
        return MemoryType.IDENTITY
    if matches_any(normalized, PROCEDURAL_PHRASES):
        return MemoryType.PROCEDURAL
    if matches_any(normalized, EPISODE_PHRASES):
        return MemoryType.EPISODE
    if LOCATION_PATTERN.search(normalized):
        return MemoryType.SEMANTIC
    return MemoryType.SEMANTIC


def base_importance_for_type(memory_type: MemoryType) -> float:
    return BASE_IMPORTANCE.get(memory_type, 0.5)
