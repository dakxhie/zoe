"""Pytest coverage for project analysis planning and execution."""

from __future__ import annotations

from agents.analyzer import run_project_analysis
from agents.planner import build_plan, is_project_analysis_query

EXPECTED_STEPS = [
    "Search code",
    "Read important files",
    "Gather context",
    "Summarize",
    "Recommend improvements",
]


def test_project_analysis_query_detection() -> None:
    """Detect project analysis requests."""
    query = "Analyze this Python project and tell me how to improve it."
    assert is_project_analysis_query(query)


def test_project_analysis_plan() -> None:
    """Return the fixed project analysis plan."""
    assert build_plan() == EXPECTED_STEPS


def test_run_project_analysis() -> None:
    """Plan and gather context for project analysis."""
    query = "Analyze this Python project and tell me how to improve it."
    is_analysis, context = run_project_analysis(query)

    assert is_analysis
    for step in EXPECTED_STEPS:
        assert step in context
    assert "Project Analysis" in context
    assert "README.md" in context
