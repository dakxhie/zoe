"""Reasoning specialist: logic, comparisons, planning frames."""

from __future__ import annotations

from agents.agent_result import AgentResult, Finding
from agents.specialists.base import clamp_confidence
from agents.state import Intent
from core.text_utils import matches_any, normalize_text

REASONING_PHRASES: tuple[str, ...] = (
    "compare",
    "versus",
    " vs ",
    "why ",
    "pros and cons",
    "evaluate",
    "which is better",
    "step by step",
    "plan",
    "logic",
    "reason",
    "tradeoff",
    "option",
    "calculate",
    "equation",
    "prove",
    "deduce",
    "decision",
)


class ReasoningSpecialist:
    name = "reasoning"

    def run(self, query: str, intent: Intent | None) -> AgentResult:
        normalized = normalize_text(query)
        findings: list[Finding] = []
        confidence = 0.5

        if intent and intent.type.value in {
            "comparison",
            "complex_reasoning",
            "step_by_step",
            "multi_tool",
        }:
            confidence = 0.8

        if matches_any(normalized, ("compare", "versus", " vs ", "difference between")):
            findings.append(
                Finding(
                    summary="Use a structured comparison: criteria, similarities, differences, recommendation.",
                    detail="Present both sides with evidence before concluding.",
                    topic="comparison",
                )
            )
            confidence = max(confidence, 0.82)

        if matches_any(normalized, ("step by step", "step-by-step", "walk me through")):
            findings.append(
                Finding(
                    summary="Respond with numbered steps and checkpoints.",
                    topic="planning",
                )
            )
            confidence = max(confidence, 0.75)

        if matches_any(normalized, ("pros and cons", "evaluate", "which is better", "tradeoff")):
            findings.append(
                Finding(
                    summary="Weigh options explicitly; state assumptions and confidence.",
                    topic="evaluation",
                )
            )
            confidence = max(confidence, 0.78)

        if "?" in query and matches_any(normalized, ("why", "how come", "explain why")):
            findings.append(
                Finding(
                    summary="Chain reasoning: premise → evidence → conclusion.",
                    topic="causal",
                )
            )
            confidence = max(confidence, 0.7)

        if matches_any(normalized, ("calculate", "equation", "solve for", "math")):
            findings.append(
                Finding(
                    summary="Show working steps for mathematical or logical problems.",
                    topic="mathematics",
                )
            )
            confidence = max(confidence, 0.72)

        if not findings and intent and intent.complexity.value != "low":
            findings.append(
                Finding(
                    summary="Apply clear logical structure before answering.",
                    topic="general",
                )
            )
            confidence = 0.55

        return AgentResult(
            agent=self.name,
            confidence=clamp_confidence(confidence),
            findings=findings,
        )


def reasoning_specialist_relevant(query: str, intent: Intent | None) -> bool:
    normalized = normalize_text(query)
    if intent and intent.type.value in {
        "comparison",
        "complex_reasoning",
        "step_by_step",
        "multi_tool",
        "report_generation",
    }:
        return True
    return matches_any(normalized, REASONING_PHRASES)
