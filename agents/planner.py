"""Planning for Zoe AI agent workflows."""

from __future__ import annotations

import logging
import re

from agents.state import Intent, IntentType, PlanStep
from core.text_utils import matches_any, normalize_text

logger = logging.getLogger(__name__)

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


def is_project_analysis_query(query: str) -> bool:
    """Return True when the user asks for project analysis or improvements."""
    normalized = normalize_text(query)
    return matches_any(normalized, ANALYSIS_PHRASES)


def build_plan() -> list[str]:
    """Return the fixed project analysis plan."""
    return list(PROJECT_ANALYSIS_PLAN)


def _pdf_chapter_steps(query: str) -> list[PlanStep]:
    chapters = [match.group(1) for match in re.finditer(r"chapter\s+(\d+)", query, flags=re.IGNORECASE)]
    steps: list[PlanStep] = []
    for index, chapter in enumerate(chapters[:2], start=1):
        steps.append(
            PlanStep(
                order=index,
                action="retrieve",
                tool="pdf",
                detail=f"chapter {chapter}",
            )
        )
    return steps


def create_plan(intent: Intent, query: str) -> list[PlanStep]:
    """Create an internal execution plan for a classified intent."""
    steps: list[PlanStep] = []
    order = 1

    if intent.type == IntentType.PROJECT_ANALYSIS:
        for label in PROJECT_ANALYSIS_PLAN:
            tool = "project_analysis" if label == "Search code" else "code" if "code" in label.lower() else "project_analysis"
            steps.append(PlanStep(order=order, action="analyze", tool=tool, detail=label))
            order += 1
        logger.debug("Planner created project analysis plan with %s steps", len(steps))
        return steps

    if intent.type in {IntentType.COMPARISON, IntentType.MULTI_TOOL} and "chapter" in normalize_text(query):
        steps.extend(_pdf_chapter_steps(query))
        order = len(steps) + 1
        steps.append(PlanStep(order=order, action="compare", tool="llm", detail="compare retrieved sections"))
        order += 1
        steps.append(PlanStep(order=order, action="summarize", tool="llm", detail="summarize findings"))
        logger.debug("Planner created comparison plan with %s steps", len(steps))
        return steps

    for tool in intent.required_tools:
        action = "retrieve"
        if tool == "project_analysis":
            action = "analyze"
        steps.append(PlanStep(order=order, action=action, tool=tool, detail=query))
        order += 1

    if intent.type in {
        IntentType.SUMMARIZATION,
        IntentType.COMPARISON,
        IntentType.REPORT_GENERATION,
        IntentType.STEP_BY_STEP,
        IntentType.COMPLEX_REASONING,
        IntentType.MULTI_TOOL,
    }:
        steps.append(PlanStep(order=order, action="synthesize", tool="llm", detail="generate answer"))

    if not steps:
        steps.append(PlanStep(order=1, action="respond", tool="chat", detail=query))

    logger.debug("Planner created %s-step plan for intent %s", len(steps), intent.type.value)
    return steps
