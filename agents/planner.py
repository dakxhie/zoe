"""Planning for Zoe AI agent workflows."""

from __future__ import annotations

ANALYSIS_PHRASES: tuple[str, ...] = (
    "analyze this project",
    "analyze the project",
    "analyze this python project",
    "review this project",
    "review the project",
    "how to improve",
    "improve this project",
    "improve the project",
    "project analysis",
    "improvement suggestions",
)

PROJECT_ANALYSIS_PLAN: tuple[str, ...] = (
    "Search code",
    "Read important files",
    "Gather context",
    "Summarize",
    "Recommend improvements",
)


def _normalize(query: str) -> str:
    """Normalize user input for phrase matching."""
    return " ".join(query.strip().lower().split())


def is_project_analysis_query(query: str) -> bool:
    """Return True when the user asks for project analysis or improvements."""
    normalized = _normalize(query)
    return any(phrase in normalized for phrase in ANALYSIS_PHRASES)


def build_plan() -> list[str]:
    """Return the fixed project analysis plan."""
    return list(PROJECT_ANALYSIS_PLAN)
