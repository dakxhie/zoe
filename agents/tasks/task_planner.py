"""Plan autonomous multi-step goals into internal subtasks."""

from __future__ import annotations

from agents.planner import is_project_analysis_query
from agents.tasks.task import SubTask, Task
from core.text_utils import matches_any, normalize_text

AUTONOMOUS_PHRASES: tuple[str, ...] = (
    "entire project",
    "whole project",
    "full analysis",
    "deep analysis",
    "comprehensive",
    "step by step",
    "multi-step",
    "autonomous",
    "analyze my entire",
    "suggest improvements",
)


def should_autonomous_execute(query: str, *, intent_type: str | None = None) -> bool:
    """Return True when the request should use the autonomous task engine."""
    from tools.calculator import is_calculator_request
    from tools.datetime_tool import get_datetime_response

    normalized = normalize_text(query)
    if is_calculator_request(query):
        return False
    if get_datetime_response(query) is not None:
        return False
    if normalized in {"hi", "hello", "hey", "thanks", "thank you"}:
        return False
    if len(normalized) < 12 and "?" not in query:
        return False
    if "weather" in normalized and len(normalized) < 40:
        return False

    if is_project_analysis_query(query):
        return True
    if intent_type in {"project_analysis", "multi_tool", "report_generation"}:
        return True
    return matches_any(normalized, AUTONOMOUS_PHRASES)


def plan_project_analysis_task(query: str) -> Task:
    """Build dependency chain for full project analysis."""
    s1 = SubTask.create(
        "Index project",
        "Index repository source for code search",
        "index_project",
        estimated_seconds=45.0,
    )
    s2 = SubTask.create(
        "Detect framework",
        "Detect language, framework, and structure",
        "detect_framework",
        depends_on=(s1.id,),
        estimated_seconds=15.0,
    )
    s3 = SubTask.create(
        "Analyze architecture",
        "Gather architecture and module context",
        "analyze_architecture",
        depends_on=(s2.id,),
        estimated_seconds=40.0,
    )
    s4 = SubTask.create(
        "Review code quality",
        "Scan indexed code for hotspots and tests",
        "review_code_quality",
        depends_on=(s1.id,),
        estimated_seconds=25.0,
    )
    s5 = SubTask.create(
        "Summarize",
        "Produce final improvement report",
        "summarize_report",
        depends_on=(s3.id, s4.id),
        estimated_seconds=20.0,
    )
    return Task.create(
        title="Project analysis",
        description="Autonomous project analysis and recommendations",
        goal_query=query,
        priority=10,
        subtasks=[s1, s2, s3, s4, s5],
    )


def plan_from_goal(query: str) -> Task | None:
    """Create a task graph for a user goal, or None if not autonomous."""
    if not should_autonomous_execute(query):
        return None
    if is_project_analysis_query(query) or matches_any(
        normalize_text(query),
        ("entire", "whole project", "improvements", "analyze"),
    ):
        return plan_project_analysis_task(query)
    return None
