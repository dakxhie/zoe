"""Reinforce existing memories when users repeat the same facts."""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher

from memory.intelligence.memory_scoring import score_memory_text
from memory.intelligence.memory_types import ScoredMemory

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.72

TOPIC_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(i love|i like|favorite|prefer)\b.*\bpython\b", re.I), "python_preference"),
    (re.compile(r"\b(i love|i like|favorite|prefer)\b", re.I), "preference"),
    (re.compile(r"\bmy name is\b", re.I), "identity_name"),
    (re.compile(r"\b(i live in|from)\b", re.I), "location"),
)


def _normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _topic_key(text: str) -> str | None:
    for pattern, key in TOPIC_PATTERNS:
        if pattern.search(text):
            return key
    return None


def memories_are_reinforcement_related(a: str, b: str) -> bool:
    """Return True when two texts express the same fact for reinforcement."""
    na, nb = _normalize_key(a), _normalize_key(b)
    if na == nb:
        return True

    key_a, key_b = _topic_key(a), _topic_key(b)
    if key_a and key_a == key_b:
        ratio = SequenceMatcher(None, na, nb).ratio()
        return ratio >= SIMILARITY_THRESHOLD

    return SequenceMatcher(None, na, nb).ratio() >= 0.92


def reinforce_scored_memory(
    existing_text: str,
    existing_meta: dict[str, str],
    candidate_text: str,
    *,
    explicit: bool = False,
) -> ScoredMemory | None:
    """
    If candidate reinforces existing_text, return updated ScoredMemory; else None.
    """
    if not memories_are_reinforcement_related(existing_text, candidate_text):
        return None

    try:
        frequency = int(existing_meta.get("frequency", "1")) + 1
    except ValueError:
        frequency = 2

    try:
        old_confidence = float(existing_meta.get("confidence", "0.7"))
    except ValueError:
        old_confidence = 0.7

    merged_text = existing_text
    if len(candidate_text) > len(existing_text):
        merged_text = candidate_text

    scored = score_memory_text(
        merged_text,
        explicit=explicit,
        frequency=frequency,
        existing_confidence=min(1.0, old_confidence + 0.05),
    )
    scored.created = existing_meta.get("created_at", scored.created)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Reinforced memory: frequency=%s importance=%.2f",
            scored.frequency,
            scored.importance,
        )

    return scored
