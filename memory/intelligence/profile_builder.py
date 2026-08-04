"""Build and maintain an internal long-term user profile from memories."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from core.text_utils import normalize_text
from memory.intelligence.memory_types import MemoryType

logger = logging.getLogger(__name__)

PROFILE_QUERY_PHRASES: tuple[str, ...] = (
    "what do you know about me",
    "what do you remember about me",
    "tell me about myself",
    "my profile",
    "what have you stored about me",
)

LEARNED_QUERY_PHRASES: tuple[str, ...] = (
    "what have you learned",
    "what did you learn",
    "what have you learned about me",
    "summarize what you know",
)

NAME_PATTERN = re.compile(r"\bmy name is\s+([^.?!,\n]+)", re.I)
CALL_ME_PATTERN = re.compile(r"\bcall me\s+([^.?!,\n]+)", re.I)
LIVE_IN_PATTERN = re.compile(r"\bi live in\s+([^.?!,\n]+)", re.I)
FROM_PATTERN = re.compile(r"\bi(?:'m| am) from\s+([^.?!,\n]+)", re.I)
BUILDING_PATTERN = re.compile(r"\bi am building\s+([^.?!,\n]+)", re.I)
WORK_ON_PATTERN = re.compile(r"\bi work on\s+([^.?!,\n]+)", re.I)
FAVORITE_PATTERN = re.compile(
    r"\bmy favorite\s+(\w+)\s+is\s+([^.?!,\n]+)",
    re.I,
)
PREFER_PATTERN = re.compile(r"\bi prefer\s+([^.?!,\n]+)", re.I)
GOAL_PATTERN = re.compile(r"\bmy goal is\s+([^.?!,\n]+)", re.I)
THEME_PATTERN = re.compile(r"\b(dark|light)\s+theme\b", re.I)
IDE_PATTERN = re.compile(r"\b(use|using|prefer)\s+(cursor|vscode|pycharm|vim|neovim)\b", re.I)


@dataclass
class UserProfile:
    """Internal profile — not exposed automatically in normal chat."""

    name: str = ""
    location: str = ""
    occupation: str = ""
    projects: list[str] = field(default_factory=list)
    programming: list[str] = field(default_factory=list)
    favorite_ide: str = ""
    favorite_languages: list[str] = field(default_factory=list)
    preferred_os: str = ""
    theme: str = ""
    goals: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    books: list[str] = field(default_factory=list)
    personality_notes: list[str] = field(default_factory=list)
    episodes: list[str] = field(default_factory=list)
    semantic_facts: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any(
            [
                self.name,
                self.location,
                self.occupation,
                self.projects,
                self.programming,
                self.favorite_ide,
                self.favorite_languages,
                self.preferred_os,
                self.theme,
                self.goals,
                self.interests,
                self.books,
                self.personality_notes,
                self.episodes,
                self.semantic_facts,
            ]
        )


def is_profile_summary_query(text: str) -> bool:
    normalized = normalize_text(text)
    return any(phrase in normalized for phrase in PROFILE_QUERY_PHRASES)


def is_learned_summary_query(text: str) -> bool:
    normalized = normalize_text(text)
    if is_profile_summary_query(text):
        return True
    return any(phrase in normalized for phrase in LEARNED_QUERY_PHRASES)


def _add_unique(bucket: list[str], value: str) -> None:
    cleaned = value.strip()
    if cleaned and cleaned not in bucket:
        bucket.append(cleaned)


def _apply_text_to_profile(profile: UserProfile, text: str, memory_type: str = "") -> None:
    if match := NAME_PATTERN.search(text):
        profile.name = match.group(1).strip().title()
    if match := CALL_ME_PATTERN.search(text):
        profile.name = match.group(1).strip().title()
    if match := LIVE_IN_PATTERN.search(text):
        profile.location = match.group(1).strip()
    if match := FROM_PATTERN.search(text):
        profile.location = match.group(1).strip()
    if match := BUILDING_PATTERN.search(text):
        _add_unique(profile.projects, match.group(1).strip())
    if match := WORK_ON_PATTERN.search(text):
        _add_unique(profile.projects, match.group(1).strip())
    if match := FAVORITE_PATTERN.search(text):
        kind, value = match.group(1).lower(), match.group(2).strip()
        if kind in {"language", "programming", "programming language"}:
            _add_unique(profile.favorite_languages, value)
        elif kind == "book":
            _add_unique(profile.books, value)
        elif kind == "color":
            _add_unique(profile.interests, f"favorite color: {value}")
        else:
            _add_unique(profile.interests, f"favorite {kind}: {value}")
    if match := PREFER_PATTERN.search(text):
        pref = match.group(1).strip()
        if "python" in pref.lower():
            _add_unique(profile.favorite_languages, "Python")
        _add_unique(profile.interests, pref)
    if match := GOAL_PATTERN.search(text):
        _add_unique(profile.goals, match.group(1).strip())
    if match := THEME_PATTERN.search(text):
        profile.theme = f"{match.group(1).lower()} theme"
    if match := IDE_PATTERN.search(text):
        profile.favorite_ide = match.group(2).strip()

    lower = text.lower()
    if "python" in lower and ("love" in lower or "like" in lower or "favorite" in lower):
        _add_unique(profile.favorite_languages, "Python")
    if "zoe" in lower and "building" in lower:
        _add_unique(profile.projects, "Zoe AI")

    if memory_type == MemoryType.EPISODE.value:
        _add_unique(profile.episodes, text[:200])
    elif memory_type == MemoryType.IDENTITY.value and not profile.name:
        _add_unique(profile.semantic_facts, text[:200])
    elif memory_type in {MemoryType.SEMANTIC.value, MemoryType.PROJECT.value}:
        _add_unique(profile.semantic_facts, text[:200])


def build_user_profile(records: list[dict[str, str]]) -> UserProfile:
    """
    Build profile from memory records.

    Each record expects keys: text, category (optional), importance (optional).
    """
    profile = UserProfile()
    sorted_records = sorted(
        records,
        key=lambda r: float(r.get("importance", "0") or 0),
        reverse=True,
    )
    for record in sorted_records:
        text = record.get("text") or record.get("content") or ""
        if not text.strip():
            continue
        category = record.get("category", record.get("memory_type", ""))
        _apply_text_to_profile(profile, text, memory_type=category)

    if logger.isEnabledFor(logging.DEBUG) and not profile.is_empty():
        logger.debug("Profile updated: name=%s projects=%s", profile.name or "—", len(profile.projects))

    return profile


def format_profile_summary_for_user(profile: UserProfile) -> str:
    """User-facing summary when they ask what Zoe knows."""
    if profile.is_empty():
        return (
            "I don't have much stored about you yet. "
            "Tell me about yourself — for example your name, goals, or favorite tools — "
            "and I'll remember the important parts."
        )

    lines: list[str] = ["Here's what I've learned about you:"]

    if profile.name:
        lines.append(f"- **Name:** {profile.name}")
    if profile.location:
        lines.append(f"- **Location:** {profile.location}")
    if profile.occupation:
        lines.append(f"- **Occupation:** {profile.occupation}")
    if profile.projects:
        lines.append(f"- **Projects:** {', '.join(profile.projects[:8])}")
    if profile.favorite_languages:
        lines.append(f"- **Languages:** {', '.join(profile.favorite_languages[:8])}")
    if profile.favorite_ide:
        lines.append(f"- **IDE / editor:** {profile.favorite_ide}")
    if profile.theme:
        lines.append(f"- **Theme:** {profile.theme}")
    if profile.goals:
        lines.append(f"- **Goals:** {', '.join(profile.goals[:5])}")
    if profile.interests:
        lines.append(f"- **Interests & preferences:** {', '.join(profile.interests[:8])}")
    if profile.books:
        lines.append(f"- **Books:** {', '.join(profile.books[:5])}")
    if profile.episodes:
        lines.append(f"- **Recent episodes:** {profile.episodes[0][:160]}")

    if len(lines) == 1:
        lines.append("- " + (profile.semantic_facts[0][:200] if profile.semantic_facts else "General facts from our chats."))

    return "\n".join(lines)
