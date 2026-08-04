"""Supervisor agent: routing, merging, and conflict resolution."""

from __future__ import annotations

import logging
from typing import Iterable

from agents.agent_result import AgentResult, Finding, SupervisorBrief, SupervisorDecision
from agents.coordinator import run_specialists_parallel
from agents.specialists.coding_agent import coding_specialist_relevant
from agents.specialists.creative_agent import creative_specialist_relevant
from agents.specialists.memory_agent import memory_specialist_relevant
from agents.specialists.reasoning_agent import reasoning_specialist_relevant
from agents.specialists.research_agent import research_specialist_relevant
from agents.state import AgentState, Complexity, Intent, IntentType
from core.text_utils import normalize_text
from tools.calculator import is_calculator_request

logger = logging.getLogger(__name__)

SPECIALIST_ORDER: tuple[str, ...] = ("memory", "research", "coding", "reasoning", "creative")


def requires_autonomous_execution(query: str, intent: Intent | None) -> bool:
    """Return True when the supervisor should route to the task engine."""
    from agents.tasks.task_planner import should_autonomous_execute

    intent_type = intent.type.value if intent else None
    return should_autonomous_execute(query, intent_type=intent_type)


def should_use_supervisor(intent: Intent, query: str) -> bool:
    """Return True when internal specialist agents should run."""
    if intent.type in {IntentType.CALCULATOR, IntentType.DATETIME}:
        return False
    if is_calculator_request(query):
        return False

    selected = select_specialists(query, intent)
    if not selected:
        return False

    if (
        intent.type == IntentType.CONVERSATION
        and intent.complexity == Complexity.LOW
        and len(intent.required_tools) <= 1
        and intent.primary_route == "chat"
        and selected == ("reasoning",)
    ):
        return False

    if intent.type == IntentType.CONVERSATION and intent.primary_route == "chat":
        normalized = normalize_text(query)
        if len(normalized) < 24 and selected == ("reasoning",):
            return False

    return True


def select_specialists(query: str, intent: Intent | None) -> tuple[str, ...]:
    """Choose specialist agents for a user query."""
    chosen: list[str] = []

    if memory_specialist_relevant(query, intent):
        chosen.append("memory")
    if research_specialist_relevant(query, intent):
        chosen.append("research")
    if coding_specialist_relevant(query, intent):
        chosen.append("coding")
        if "reasoning" not in chosen:
            chosen.append("reasoning")
    if reasoning_specialist_relevant(query, intent):
        chosen.append("reasoning")
    if creative_specialist_relevant(query, intent):
        chosen.append("creative")
        if "reasoning" not in chosen:
            chosen.append("reasoning")

    if intent and intent.type == IntentType.PROJECT_ANALYSIS:
        for name in ("coding", "research", "reasoning", "memory"):
            if name not in chosen:
                chosen.append(name)

    ordered = [name for name in SPECIALIST_ORDER if name in chosen]
    return tuple(ordered)


def resolve_conflicts(results: Iterable[AgentResult]) -> list[AgentResult]:
    """Drop lower-confidence duplicate topic findings across agents."""
    topic_best: dict[str, tuple[float, Finding]] = {}

    for result in results:
        for finding in result.findings:
            topic = finding.topic or finding.summary[:40].lower()
            current = topic_best.get(topic)
            if current is None or result.confidence > current[0]:
                topic_best[topic] = (result.confidence, finding)

    if not topic_best:
        return list(results)

    merged: list[AgentResult] = []
    for result in results:
        kept: list[Finding] = []
        for finding in result.findings:
            topic = finding.topic or finding.summary[:40].lower()
            best = topic_best.get(topic)
            if best and best[1] is finding:
                kept.append(finding)
        if kept or result.warnings or result.citations:
            merged.append(
                AgentResult(
                    agent=result.agent,
                    confidence=result.confidence,
                    findings=kept,
                    citations=result.citations,
                    warnings=result.warnings,
                )
            )
    return merged


def merge_results(results: list[AgentResult]) -> str:
    """Merge specialist outputs into one internal context block."""
    if not results:
        return ""

    resolved = resolve_conflicts(results)
    ranked = sorted(resolved, key=lambda item: item.confidence, reverse=True)
    blocks = [item.context_block() for item in ranked if item.context_block().strip()]
    header = (
        "========================\n"
        "Internal Specialist Brief\n"
        "========================\n"
        "The following notes were prepared by internal specialists. "
        "Synthesize them into one user-facing answer; do not mention agents.\n"
    )
    return header + "\n\n" + "\n\n".join(blocks)


def _log_supervisor_debug(
    decision: SupervisorDecision,
    results: list[AgentResult],
    *,
    merged_context: str,
) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return

    logger.debug("Supervisor")
    logger.debug(
        "Selected agents: %s",
        ", ".join(decision.selected_agents) or "(none)",
    )
    if decision.skipped_reason:
        logger.debug("Skip reason: %s", decision.skipped_reason)
    logger.debug(
        "Execution order: %s",
        " -> ".join(decision.selected_agents) or "(idle)",
    )
    for result in results:
        logger.debug(
            "%s confidence: %.2f (%s findings, %s citations)",
            result.agent.title(),
            result.confidence,
            len(result.findings),
            len(result.citations),
        )
    finding_count = sum(len(item.findings) for item in results)
    logger.debug(
        "Merge summary: %s findings from %s specialists, %s chars context",
        finding_count,
        len(results),
        len(merged_context),
    )


def run_supervisor_cycle(query: str, intent: Intent, state: AgentState) -> SupervisorBrief:
    """Decompose the task, run specialists, merge, and attach to agent state."""
    selected = select_specialists(query, intent)
    decision = SupervisorDecision(query=query, selected_agents=selected)

    if not selected:
        decision = SupervisorDecision(
            query=query,
            selected_agents=(),
            skipped_reason="No specialists required",
        )
        return SupervisorBrief(context="", results=[], decision=decision)

    results = run_specialists_parallel(query, intent, selected)
    context = merge_results(results)
    _log_supervisor_debug(decision, results, merged_context=context)

    state.metadata["supervisor"] = {
        "agents": list(selected),
        "confidences": {item.agent: item.confidence for item in results},
    }

    return SupervisorBrief(context=context, results=results, decision=decision)


def append_supervisor_context(state: AgentState, brief: SupervisorBrief) -> None:
    """Attach merged specialist context to existing fused tool context."""
    if not brief.context.strip():
        return
    if state.fused_context.strip():
        state.fused_context = f"{state.fused_context}\n\n{brief.context}"
    else:
        state.fused_context = brief.context
