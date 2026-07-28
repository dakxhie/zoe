"""Pytest coverage for the Zoe tool router."""

from __future__ import annotations

import pytest

from tools.router import route_query

TEST_CASES: tuple[tuple[str, str], ...] = (
    ("What is my favorite color?", "memory"),
    ("Summarize Chapter 2.", "pdf"),
    ("Find generate_response().", "code"),
    ("Tell me about my notes.", "notes"),
    ("Hello!", "chat"),
)


@pytest.mark.parametrize(("query", "expected"), TEST_CASES)
def test_route_query(query: str, expected: str) -> None:
    """Route queries to the expected tool."""
    assert route_query(query) == expected
