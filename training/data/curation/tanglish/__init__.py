"""Tanglish track helpers (Sprint 25). Separate from the original Sprint 23 SFT bank."""

from __future__ import annotations

from typing import Any

from training.data.curation import DEFAULT_SYSTEM, SERIOUS_SYSTEM, sft as _sft

TANGLISH_SYSTEM = (
    DEFAULT_SYSTEM
    + " When the user writes Tanglish (Tamil–English code-mix in Latin script), "
    "reply in natural Tanglish code-switching unless they ask for English-only "
    "or the topic is safety-critical / professional client-facing. "
    "Accept romanization variation (epdi/eppadi, iruku/irukku, etc.). "
    "Do not treat Tanglish as a translation homework unless asked."
)

TANGLISH_SERIOUS = (
    SERIOUS_SYSTEM
    + " If the user wrote Tanglish, you may reply in calm Tanglish or clear English; "
    "prefer clarity over casual slang. No jokes."
)


def tanglish_sft(
    eid: str,
    user: str,
    assistant: str,
    *,
    category: str = "general_conversation",
    personality_mode: str = "professional_neutral",
    difficulty: str = "medium",
    expected_behavior: str = "tanglish_fluency",
    safety_sensitive: bool = False,
    personality_required: bool = False,
    tool_required: bool = False,
    subtopic: str = "casual",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta_extra = {"track": "tanglish", "subtopic": subtopic}
    if extra:
        meta_extra.update(extra)
    system = TANGLISH_SERIOUS if personality_mode == "serious_no_humor" else TANGLISH_SYSTEM
    return _sft(
        eid,
        user,
        assistant,
        category=category,
        personality_mode=personality_mode,
        difficulty=difficulty,
        source="sprint25_tanglish_curated",
        quality=0.93,
        personality_required=personality_required,
        tool_required=tool_required,
        expected_behavior=expected_behavior,
        safety_sensitive=safety_sensitive,
        system=system,
        extra=meta_extra,
    )
