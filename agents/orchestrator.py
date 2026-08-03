"""Agent orchestration entry point for the Zoe chat pipeline."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass

from agents.analyzer import run_project_analysis
from agents.executor import execute_agent_plan
from agents.intent import analyze_intent
from agents.planner import create_plan
from agents.state import AgentState, IntentType
from agents.verifier import verify_agent_state
from brain.context import get_empty_index_response
from memory.history import get_history
from tools.router import extract_image_path

logger = logging.getLogger(__name__)


@dataclass
class OrchestratedTurn:
    """Result of agent orchestration for one chat turn."""

    messages: list[dict[str, str]] | None = None
    direct_reply: str | None = None
    empty_index_response: str | None = None
    use_vision_path: str | None = None
    state: AgentState | None = None


def _log_agent_debug(state: AgentState) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return

    intent = state.intent
    if intent:
        logger.debug("Agent intent: %s (confidence=%.2f)", intent.type.value, intent.confidence)
        logger.debug("Selected tools: %s", intent.required_tools)

    logger.debug("Execution order: %s", [f"{step.tool}:{step.action}" for step in state.plan])
    if state.execution:
        logger.debug("Recovery warnings: %s", state.execution.warnings)
        logger.debug("Execution errors: %s", state.execution.errors)

    timings = state.timings
    logger.debug(
        "Timings ms planner=%.1f tool=%.1f retrieval=%.1f total=%.1f",
        timings.planner_ms,
        timings.tool_ms,
        timings.retrieval_ms,
        timings.total_ms,
    )


def orchestrate_chat_turn(prompt: str) -> OrchestratedTurn:
    """Run intent analysis, planning, execution, verification, and prompt building."""
    total_start = time.perf_counter()
    state = AgentState(conversation_id=str(uuid.uuid4()), goal=prompt)

    planner_start = time.perf_counter()
    state.intent = analyze_intent(prompt)
    state.plan = create_plan(state.intent, prompt)
    state.timings.planner_ms = (time.perf_counter() - planner_start) * 1000

    if state.intent.primary_route == "vision":
        image_path = extract_image_path(prompt)
        if image_path:
            return OrchestratedTurn(use_vision_path=image_path, state=state)

    is_analysis, analysis_context = run_project_analysis(prompt)
    state.analysis_context = analysis_context if is_analysis else ""

    if not is_analysis:
        empty_index_response = get_empty_index_response(prompt, state.intent.primary_route)
        if empty_index_response is not None and len(state.intent.required_tools) <= 1:
            state.timings.total_ms = (time.perf_counter() - total_start) * 1000
            return OrchestratedTurn(empty_index_response=empty_index_response, state=state)

    if is_analysis:
        pass
    elif len(state.intent.required_tools) > 1 or state.intent.type in {
        IntentType.MULTI_TOOL,
        IntentType.COMPARISON,
        IntentType.SUMMARIZATION,
        IntentType.REPORT_GENERATION,
        IntentType.STEP_BY_STEP,
        IntentType.COMPLEX_REASONING,
    }:
        execute_agent_plan(state)

    verification = verify_agent_state(state)
    if verification.needs_clarification and not state.analysis_context.strip() and not state.fused_context.strip():
        state.timings.total_ms = (time.perf_counter() - total_start) * 1000
        _log_agent_debug(state)
        return OrchestratedTurn(direct_reply=verification.clarification_message, state=state)

    from brain.context import _build_chat_messages

    history = get_history(max_messages=20)
    fused = state.fused_context
    if state.analysis_context.strip():
        messages = _build_chat_messages(
            prompt,
            history,
            analysis_context=state.analysis_context,
            selected_route=state.intent.primary_route if state.intent else None,
        )
    elif fused.strip() and len(state.intent.required_tools) > 1:
        messages = _build_chat_messages(
            prompt,
            history,
            selected_route=state.intent.primary_route if state.intent else None,
            agent_context=fused,
        )
    elif state.intent and state.intent.primary_route == "web":
        messages = _build_chat_messages(
            prompt,
            history,
            selected_route="web",
        )
    elif fused.strip():
        messages = _build_chat_messages(
            prompt,
            history,
            selected_route=state.intent.primary_route if state.intent else None,
            agent_context=fused,
        )
    else:
        messages = _build_chat_messages(
            prompt,
            history,
            selected_route=state.intent.primary_route if state.intent else None,
        )

    state.timings.total_ms = (time.perf_counter() - total_start) * 1000
    _log_agent_debug(state)
    return OrchestratedTurn(messages=messages, state=state)
