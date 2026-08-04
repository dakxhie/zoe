"""Memory reinforcement tests (not executed in sprint)."""

from __future__ import annotations

from memory.intelligence.reinforcement import (
    memories_are_reinforcement_related,
    reinforce_scored_memory,
)


def test_same_text_reinforces() -> None:
    assert memories_are_reinforcement_related("I love Python", "I love Python")


def test_python_preference_variants_reinforce() -> None:
    assert memories_are_reinforcement_related("I like Python", "My favorite language is Python")


def test_reinforce_increments_frequency() -> None:
    meta = {
        "frequency": "2",
        "confidence": "0.75",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    updated = reinforce_scored_memory("I love Python", meta, "I love Python")
    assert updated is not None
    assert updated.frequency == 3
    assert updated.importance >= 0.8
