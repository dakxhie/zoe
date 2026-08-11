"""Metric definitions for Zoe fine-tuning evaluation.

Designed for later scoring (human + automatic). No metric is computed on import.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

METRIC_NAMES: tuple[str, ...] = (
    "instruction_adherence",
    "tool_routing_accuracy",
    "structured_output_validity",
    "grounding",
    "memory_decision_accuracy",
    "response_quality",
    "personality_score",
    "humor_appropriateness",
    "sarcasm_appropriateness",
    "hallucination_rate",
    "regression_rate",
)

# Sprint 24 comparison table dimensions (1–5 human scores).
RUBRIC_DIMENSIONS: tuple[str, ...] = (
    "correctness",
    "helpfulness",
    "clarity",
    "concision",
    "professionalism",
    "intelligence",
    "confidence",
    "wit",
    "humor",
    "sarcasm",
    "naturalness",
    "emotional_calibration",
    "hallucination_resistance",
    "uncertainty_handling",
    "grounding",
    "tool_awareness",
    "instruction_following",
)

PERSONALITY_EVAL_CHECKS: tuple[str, ...] = (
    "has_personality_when_appropriate",
    "remains_professional",
    "sarcasm_appropriate",
    "humor_drops_when_serious",
    "accurate_while_witty",
    "avoids_repetitive_jokes",
    "answer_before_personality",
    "not_comedian_first",
)

TOOL_PRESERVATION_CHECKS: tuple[str, ...] = (
    "does_not_invent_calculator_result",
    "does_not_invent_current_time",
    "does_not_claim_web_search_without_tool",
    "does_not_claim_plugin_execution_without_tool",
    "does_not_claim_db_or_filesystem_read_without_tool",
    "admits_need_for_tool_when_appropriate",
)


@dataclass
class MetricScore:
    name: str
    value: float | None
    notes: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExampleJudgement:
    example_id: str
    mode: str  # base | adapter
    scores: list[MetricScore] = field(default_factory=list)
    personality_checks: dict[str, bool | None] = field(default_factory=dict)
    raw_response: str = ""


def empty_scorecard() -> dict[str, None]:
    return {name: None for name in METRIC_NAMES}


def empty_rubric() -> dict[str, None]:
    return {name: None for name in RUBRIC_DIMENSIONS}


def score_structured_output_validity(
    response: str, required_keys: list[str] | None = None
) -> MetricScore:
    """Lightweight automatic check when JSON/object output is expected."""
    required_keys = required_keys or []
    text = response.strip()
    if not required_keys:
        if text.startswith("{") and text.endswith("}"):
            try:
                import json

                json.loads(text)
                return MetricScore("structured_output_validity", 1.0, "valid_json_object")
            except Exception:  # noqa: BLE001
                return MetricScore("structured_output_validity", 0.0, "invalid_json")
        return MetricScore("structured_output_validity", None, "no_schema_provided")

    missing = [k for k in required_keys if k not in text]
    value = 1.0 if not missing else max(0.0, 1.0 - len(missing) / len(required_keys))
    return MetricScore(
        "structured_output_validity",
        value,
        notes="missing=" + ",".join(missing) if missing else "ok",
    )


_TOOL_CLAIM = re.compile(
    r"\bi (?:just )?(?:ran|checked|searched|executed|queried) "
    r"(?:the )?(?:calculator|database|plugin|web|filesystem|chroma)\b",
    re.I,
)


def score_tool_claim_heuristic(response: str) -> MetricScore:
    """Flag possible fabricated tool execution claims (offline eval has no tools)."""
    if _TOOL_CLAIM.search(response or ""):
        return MetricScore(
            "tool_claim_heuristic",
            0.0,
            notes="possible_fabricated_tool_claim",
        )
    return MetricScore("tool_claim_heuristic", 1.0, notes="no_explicit_tool_execution_claim")


def placeholder_human_metrics() -> list[MetricScore]:
    """Return unset metrics that require human or LLM-as-judge later."""
    auto = {"structured_output_validity"}
    return [
        MetricScore(name, None, notes="requires_human_or_judge")
        for name in METRIC_NAMES
        if name not in auto
    ]
