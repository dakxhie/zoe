"""Shared helpers for Sprint 23 curated dataset export.

Running this package exports JSONL only. It does not train, download models,
or touch Zoe runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "training" / "data"

DEFAULT_SYSTEM = (
    "You are Zoe, a local personal AI assistant. Be professional, intelligent, "
    "confident, and useful. Answer first; personality second. Light wit or "
    "situational sarcasm only when appropriate—never cruel, never during serious "
    "or safety-sensitive moments, and never at the cost of accuracy. Do not invent "
    "tool results, file contents, times, calculations, or retrieved facts. Admit "
    "uncertainty. Tools, memory, and retrieval remain outside the model."
)

SERIOUS_SYSTEM = (
    "You are Zoe, a local personal AI assistant. This conversation is serious. "
    "Stay direct, calm, and professional with little or no humor. Do not invent "
    "facts or tool results. Admit uncertainty."
)


def sft(
    eid: str,
    user: str,
    assistant: str,
    *,
    category: str,
    personality_mode: str = "professional_neutral",
    difficulty: str = "medium",
    source: str = "sprint23_curated",
    quality: float = 0.92,
    personality_required: bool = False,
    tool_required: bool = False,
    expected_behavior: str = "",
    safety_sensitive: bool = False,
    system: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "category": category,
        "difficulty": difficulty,
        "source": source,
        "quality": quality,
        "personality_mode": personality_mode,
        "personality_required": personality_required,
        "tool_required": tool_required,
        "expected_behavior": expected_behavior or category,
        "safety_sensitive": safety_sensitive,
    }
    if extra:
        meta["extra"] = extra
    return {
        "id": eid,
        "messages": [
            {"role": "system", "content": system or (SERIOUS_SYSTEM if personality_mode == "serious_no_humor" else DEFAULT_SYSTEM)},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "metadata": meta,
    }


def correction(
    eid: str,
    user_request: str,
    bad_response: str,
    why_bad: str,
    ideal_response: str,
    lesson: str,
    *,
    category: str = "error_handling",
    safety_sensitive: bool = False,
) -> dict[str, Any]:
    return {
        "id": eid,
        "user_request": user_request,
        "bad_response": bad_response,
        "why_bad": why_bad,
        "ideal_response": ideal_response,
        "lesson": lesson,
        "category": category,
        "source": "sprint23_curated",
        "safety_sensitive": safety_sensitive,
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)
