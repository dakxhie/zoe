"""Importance, confidence, and category scoring for memory candidates."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from memory.intelligence.importance import base_importance_for_type, classify_memory_type
from memory.intelligence.memory_types import MemoryType, ScoredMemory

logger = logging.getLogger(__name__)

TRIVIAL_IMPORTANCE_CAP = 0.05


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def score_memory_text(
    text: str,
    *,
    explicit: bool = False,
    frequency: int = 1,
    existing_confidence: float | None = None,
) -> ScoredMemory:
    """Produce a scored memory record for a candidate text."""
    memory_type = classify_memory_type(text)
    importance = base_importance_for_type(memory_type)

    if explicit:
        importance = min(1.0, importance + 0.05)

    if frequency > 1:
        boost = min(0.25, 0.04 * (frequency - 1))
        importance = min(1.0, importance + boost)

    confidence = existing_confidence if existing_confidence is not None else 0.7
    if explicit:
        confidence = min(1.0, confidence + 0.1)
    if frequency > 1:
        confidence = min(1.0, confidence + 0.05 * (frequency - 1))

    scored = ScoredMemory(
        text=text.strip(),
        memory_type=memory_type,
        category=memory_type.value,
        importance=importance,
        confidence=confidence,
        frequency=frequency,
        last_used=_utc_now_iso(),
        created=_utc_now_iso(),
        explicit=explicit,
    )
    scored.clamp_scores()

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Memory scored: type=%s importance=%.2f confidence=%.2f",
            scored.memory_type.value,
            scored.importance,
            scored.confidence,
        )
        logger.debug("Importance: %.2f for %s", scored.importance, scored.text[:80])

    return scored


def apply_trivial_cap(scored: ScoredMemory) -> ScoredMemory:
    """Force near-zero importance for filtered-but-explicit edge cases."""
    scored.importance = min(scored.importance, TRIVIAL_IMPORTANCE_CAP)
    scored.confidence = min(scored.confidence, TRIVIAL_IMPORTANCE_CAP)
    return scored
