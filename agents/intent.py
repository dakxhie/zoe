"""Intent analysis for Zoe AI agent orchestration."""

from __future__ import annotations

import logging
import re

from agents.planner import is_project_analysis_query
from agents.state import Complexity, Intent, IntentType
from core.text_utils import matches_any, normalize_text
from tools.calculator import is_calculator_request
from tools.datetime_tool import get_datetime_response
from tools.router import extract_image_path, route_query

logger = logging.getLogger(__name__)

MULTI_TOOL_PHRASES: tuple[str, ...] = (
    "compare",
    "and summarize",
    "then summarize",
    "step by step",
    "first",
    "after that",
)

COMPARISON_PHRASES: tuple[str, ...] = ("compare", "versus", " vs ", "difference between")
SUMMARY_PHRASES: tuple[str, ...] = ("summarize", "summary", "tl;dr", "brief overview")
REPORT_PHRASES: tuple[str, ...] = ("report", "write a report", "generate a report")
STEP_PHRASES: tuple[str, ...] = ("step by step", "step-by-step", "walk me through")
REASONING_PHRASES: tuple[str, ...] = ("why", "explain why", "reasoning", "analyze deeply")


def _detect_complexity(text: str, tool_count: int) -> Complexity:
    if tool_count >= 3 or len(text) > 180:
        return Complexity.HIGH
    if tool_count >= 2 or len(text) > 90:
        return Complexity.MEDIUM
    return Complexity.LOW


def _chapter_tools(text: str) -> tuple[str, ...]:
    if "chapter" not in text and "ch " not in text:
        return ()
    if text.count("chapter") >= 2 or re.search(r"chapter\s+\d+.*chapter\s+\d+", text):
        return ("pdf", "pdf")
    if "chapter" in text or "pdf" in text or "document" in text:
        return ("pdf",)
    return ()


def _expand_tools(primary_route: str, text: str) -> tuple[str, ...]:
    tools: list[str] = []

    if primary_route not in {"chat", "filesystem"}:
        tools.append(primary_route)

    if primary_route in {"notes", "pdf", "code", "web"}:
        tools.append("memory")

    chapter_tools = _chapter_tools(text)
    for tool in chapter_tools:
        if tool not in tools:
            tools.append(tool)

    if matches_any(text, COMPARISON_PHRASES) and "pdf" not in tools and "notes" not in tools:
        tools.extend(["notes", "pdf"])

    if is_project_analysis_query(text):
        if "code" not in tools:
            tools.append("code")
        if "project_analysis" not in tools:
            tools.append("project_analysis")

    deduped: list[str] = []
    for tool in tools:
        if tool not in deduped:
            deduped.append(tool)
    return tuple(deduped)


def _intent_type_for_route(route: str, text: str, tools: tuple[str, ...]) -> IntentType:
    if is_project_analysis_query(text):
        return IntentType.PROJECT_ANALYSIS
    if len(tools) > 1 or matches_any(text, MULTI_TOOL_PHRASES):
        if matches_any(text, COMPARISON_PHRASES):
            return IntentType.COMPARISON
        return IntentType.MULTI_TOOL
    if matches_any(text, SUMMARY_PHRASES):
        return IntentType.SUMMARIZATION
    if matches_any(text, REPORT_PHRASES):
        return IntentType.REPORT_GENERATION
    if matches_any(text, STEP_PHRASES):
        return IntentType.STEP_BY_STEP
    if matches_any(text, REASONING_PHRASES):
        return IntentType.COMPLEX_REASONING

    mapping = {
        "memory": IntentType.MEMORY_RETRIEVAL,
        "notes": IntentType.NOTES,
        "pdf": IntentType.PDF,
        "code": IntentType.CODE,
        "vision": IntentType.VISION,
        "web": IntentType.WEB,
        "filesystem": IntentType.FILESYSTEM,
        "chat": IntentType.CONVERSATION,
    }
    if route == "chat" and is_calculator_request(text):
        return IntentType.CALCULATOR
    if route == "chat" and get_datetime_response(text) is not None:
        return IntentType.DATETIME

    return mapping.get(route, IntentType.CONVERSATION)


def analyze_intent(query: str) -> Intent:
    """Classify the user query and required tools."""
    normalized = normalize_text(query)
    primary_route = route_query(query)

    if extract_image_path(query):
        primary_route = "vision"

    required_tools = _expand_tools(primary_route, normalized)
    intent_type = _intent_type_for_route(primary_route, normalized, required_tools)
    complexity = _detect_complexity(normalized, len(required_tools))

    confidence = 0.82
    if intent_type in {IntentType.MULTI_TOOL, IntentType.COMPARISON}:
        confidence = 0.7
    if intent_type == IntentType.CONVERSATION:
        confidence = 0.55

    intent = Intent(
        type=intent_type,
        confidence=confidence,
        required_tools=required_tools,
        complexity=complexity,
        primary_route=primary_route,
    )
    logger.debug(
        "Intent analyzed: type=%s route=%s tools=%s confidence=%.2f",
        intent.type.value,
        intent.primary_route,
        intent.required_tools,
        intent.confidence,
    )
    try:
        from plugins.manager import select_plugins_for_planner

        matched = select_plugins_for_planner(query)
        if matched and logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Planner plugin candidates: %s",
                ", ".join(plugin.id for plugin in matched),
            )
    except Exception:
        pass
    return intent
