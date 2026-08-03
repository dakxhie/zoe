"""Project analysis orchestration for Zoe AI."""

from __future__ import annotations

import logging

from agents.executor import execute_project_analysis
from agents.intent import analyze_intent
from agents.planner import build_plan, is_project_analysis_query
from agents.project_report import build_project_report, format_project_report

logger = logging.getLogger(__name__)


def run_project_analysis(query: str) -> tuple[bool, str]:
    """Plan and execute project analysis, returning context for the LLM."""
    if not is_project_analysis_query(query):
        return False, ""

    logger.info("Planner triggered")
    plan = build_plan()
    gathered_context = execute_project_analysis(query)
    structured = format_project_report(build_project_report())
    logger.info("Executor finished")
    logger.info("Analysis chars: %s", len(gathered_context))

    plan_lines = "\n".join(f"{index}. {step}" for index, step in enumerate(plan, start=1))
    analysis_context = (
        f"Plan:\n{plan_lines}\n\n"
        f"Structured Report:\n{structured}\n\n"
        f"{gathered_context}"
    )

    if not analysis_context.strip():
        logger.warning("Project analysis produced empty context")

    return True, analysis_context


__all__ = ["analyze_intent", "run_project_analysis", "build_project_report", "format_project_report"]
