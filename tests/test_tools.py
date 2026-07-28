"""Pytest coverage for tool execution."""

from __future__ import annotations

import pytest

from tools.executor import execute_tool

TEST_CASES: tuple[tuple[str, bool], ...] = (
    ("2+2", True),
    ("10*(5+2)", True),
    ("Current time", True),
    ("Today's date", True),
    ("Hello", False),
)


@pytest.mark.parametrize(("query", "should_handle"), TEST_CASES)
def test_execute_tool(query: str, should_handle: bool) -> None:
    """Execute lightweight tools outside the LLM."""
    handled, result = execute_tool(query)
    assert handled == should_handle
    if should_handle:
        assert result
