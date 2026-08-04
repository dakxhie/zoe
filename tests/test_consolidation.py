"""Memory consolidation tests (not executed in sprint)."""

from __future__ import annotations

from memory.intelligence.consolidation import consolidate_with_existing, try_merge_pair


def test_merge_python_preferences() -> None:
    merged = try_merge_pair("I like Python", "My favorite language is Python")
    assert merged == "Favorite programming language: Python"


def test_consolidate_with_existing_list() -> None:
    result = consolidate_with_existing(
        "I love Python",
        ["My favorite language is Python"],
    )
    assert "Python" in result
    assert "Favorite" in result
