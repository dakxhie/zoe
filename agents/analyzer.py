"""Project analysis orchestration for Zoe AI."""

from __future__ import annotations

from agents.executor import execute_project_analysis
from agents.planner import build_plan, is_project_analysis_query


def run_project_analysis(query: str) -> tuple[bool, str]:
    """Plan and execute project analysis, returning context for the LLM."""
    if not is_project_analysis_query(query):
        return False, ""

    plan = build_plan()
    gathered_context = execute_project_analysis(query)

    plan_lines = "\n".join(f"{index}. {step}" for index, step in enumerate(plan, start=1))
    analysis_context = f"Plan:\n{plan_lines}\n\n{gathered_context}"

    return True, analysis_context
