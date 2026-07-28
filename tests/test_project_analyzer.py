"""Pytest coverage for project analysis planning and execution."""

from __future__ import annotations

from agents.analyzer import run_project_analysis
from agents.planner import build_plan, is_project_analysis_query
from brain.context import (
    MAX_CONTEXT_CHARS,
    _build_analysis_system_content,
    _build_chat_messages,
    _truncate_text,
)

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


def test_project_analysis_injects_context_into_prompt() -> None:
    """Inject gathered analysis context into the system prompt."""
    query = "Analyze this Python project and tell me how to improve it."
    is_analysis, context = run_project_analysis(query)

    assert is_analysis
    truncated_context = _truncate_text(context, MAX_CONTEXT_CHARS)
    messages = _build_chat_messages(query, [], analysis_context=context)
    system_message = messages[0]["content"]

    assert "Project Analysis" in system_message
    assert "README.md" in system_message
    assert system_message == _build_analysis_system_content(truncated_context)
    assert "Do not ask the user for more files" in system_message

