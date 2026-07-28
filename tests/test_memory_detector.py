"""Pytest coverage for the memory detector."""

from __future__ import annotations

import pytest

from memory.detector import should_remember

REMEMBER_EXAMPLES: tuple[str, ...] = (
    "My favorite programming language is Python.",
    "My name is Dakshitha.",
    "I live in India.",
)

SKIP_EXAMPLES: tuple[str, ...] = (
    "What is my favorite programming language?",
    "Can you write a Python function to sort a list?",
    "Hello",
    "Tell me a joke.",
)


@pytest.mark.parametrize("sentence", REMEMBER_EXAMPLES)
def test_should_remember_personal_statements(sentence: str) -> None:
    """Remember personal statements."""
    assert should_remember(sentence)


@pytest.mark.parametrize("sentence", SKIP_EXAMPLES)
def test_should_skip_questions_and_greetings(sentence: str) -> None:
    """Skip questions, commands, and greetings."""
    assert not should_remember(sentence)
