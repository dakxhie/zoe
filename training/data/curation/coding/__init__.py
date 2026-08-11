"""Elite coding track helpers (Sprint 25)."""

from __future__ import annotations

from typing import Any

from training.data.curation import DEFAULT_SYSTEM, SERIOUS_SYSTEM, sft as _sft

CODING_SYSTEM = (
    DEFAULT_SYSTEM
    + " For coding help: prefer correct, readable, maintainable solutions. "
    "State assumptions. Distinguish prototype vs production-ready. "
    "Never claim you ran, tested, searched, or opened files unless a tool actually did. "
    "Do not invent APIs or library behavior."
)

CODING_SERIOUS = (
    SERIOUS_SYSTEM
    + " Security, data-loss, and production-incident topics: no humor. "
    "Never claim you executed code or verified a fix without a real tool run."
)


def coding_sft(
    eid: str,
    user: str,
    assistant: str,
    *,
    category: str = "coding",
    personality_mode: str = "professional_neutral",
    difficulty: str = "medium",
    expected_behavior: str = "elite_coding",
    safety_sensitive: bool = False,
    personality_required: bool = False,
    tool_required: bool = False,
    subtopic: str = "general",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta_extra = {"track": "elite_coding", "subtopic": subtopic}
    if extra:
        meta_extra.update(extra)
    system = CODING_SERIOUS if personality_mode == "serious_no_humor" or safety_sensitive else CODING_SYSTEM
    return _sft(
        eid,
        user,
        assistant,
        category=category,
        personality_mode=personality_mode,
        difficulty=difficulty,
        source="sprint25_coding_curated",
        quality=0.94,
        personality_required=personality_required,
        tool_required=tool_required,
        expected_behavior=expected_behavior,
        safety_sensitive=safety_sensitive,
        system=system,
        extra=meta_extra,
    )
