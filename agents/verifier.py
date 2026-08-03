"""Pre-response verification for agent execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from agents.state import AgentState, ExecutionResult, ToolOutput

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of pre-generation verification."""

    ok: bool
    confidence: float
    needs_clarification: bool = False
    clarification_message: str = ""
    warnings: tuple[str, ...] = ()


def _average_confidence(outputs: list[ToolOutput]) -> float:
    successful = [item.confidence for item in outputs if item.success and item.content.strip()]
    if not successful:
        return 0.0
    return sum(successful) / len(successful)


def _has_conflicting_memory(outputs: list[ToolOutput]) -> bool:
    memory_chunks = [
        output.content.lower()
        for output in outputs
        if output.tool == "memory" and output.success and output.content.strip()
    ]
    if len(memory_chunks) < 2:
        return False

    contradictions = (
        ("favorite" in chunk and "not" in chunk)
        for chunk in memory_chunks
    )
    return any(contradictions)


def verify_agent_state(state: AgentState) -> VerificationResult:
    """Verify context quality before final LLM generation."""
    warnings: list[str] = []
    execution = state.execution or ExecutionResult(success=True)
    outputs = execution.outputs or state.tool_outputs

    if execution.errors and not outputs:
        return VerificationResult(
            ok=False,
            confidence=0.0,
            needs_clarification=True,
            clarification_message=(
                "I could not gather enough context to answer confidently. "
                "Could you clarify what you'd like me to focus on?"
            ),
            warnings=tuple(execution.warnings),
        )

    empty_outputs = [item.tool for item in outputs if item.success and not item.content.strip()]
    if empty_outputs:
        warnings.append(f"Empty retrieval from: {', '.join(empty_outputs)}")

    if _has_conflicting_memory(outputs):
        warnings.append("Potentially conflicting memory entries detected")

    confidence = _average_confidence(outputs)
    if state.intent and state.intent.confidence > 0:
        confidence = max(confidence, state.intent.confidence * 0.5)

    if confidence < 0.15 and state.intent and state.intent.primary_route not in {"chat", "calculator", "datetime"}:
        if not state.fused_context.strip() and not state.analysis_context.strip():
            logger.debug("Verification: low confidence, requesting clarification")
            return VerificationResult(
                ok=False,
                confidence=confidence,
                needs_clarification=True,
                clarification_message=(
                    "I do not have enough reliable context yet. "
                    "Can you share more detail or rephrase your request?"
                ),
                warnings=tuple(warnings),
            )

    if warnings:
        logger.debug("Verification warnings: %s", warnings)

    return VerificationResult(
        ok=True,
        confidence=confidence,
        warnings=tuple(warnings),
    )
