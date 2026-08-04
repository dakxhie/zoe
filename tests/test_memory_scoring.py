"""Memory importance scoring tests (not executed in sprint)."""

from __future__ import annotations

from memory.intelligence.importance import classify_memory_type
from memory.intelligence.memory_scoring import score_memory_text
from memory.intelligence.memory_types import MemoryType


def test_identity_importance_high() -> None:
    scored = score_memory_text("My name is Dakshitha.")
    assert scored.memory_type == MemoryType.IDENTITY
    assert scored.importance >= 0.95


def test_project_importance() -> None:
    scored = score_memory_text("I am building Zoe AI.")
    assert classify_memory_type("I am building Zoe AI.") == MemoryType.PROJECT
    assert scored.importance >= 0.9


def test_preference_importance() -> None:
    scored = score_memory_text("My favorite language is Python.")
    assert scored.importance >= 0.8


def test_repeated_fact_boosts_importance() -> None:
    once = score_memory_text("I love Python")
    often = score_memory_text("I love Python", frequency=5)
    assert often.importance > once.importance
    assert often.confidence > once.confidence


def test_greeting_low_when_scored_as_semantic() -> None:
    scored = score_memory_text("hello there friend")
    assert scored.importance < 0.7
