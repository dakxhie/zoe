"""Conversational memory inference for Zoe AI."""

from __future__ import annotations

import re
from dataclasses import dataclass

from core.text_utils import normalize_text
from memory.detector import (
    CODING_PHRASES,
    EXPLANATION_PHRASES,
    JOKE_PHRASES,
    QUESTION_STARTERS,
    _should_skip,
)

AFFIRMATIONS: frozenset[str] = frozenset(
    {
        "yes",
        "yeah",
        "yep",
        "yup",
        "sure",
        "correct",
        "right",
        "definitely",
        "absolutely",
    }
)

NEGATIONS: frozenset[str] = frozenset(
    {
        "no",
        "nope",
        "nah",
        "not really",
    }
)

REPLY_PREFIXES: tuple[str, ...] = (
    "yes ",
    "yeah ",
    "yep ",
    "sure ",
    "definitely ",
    "absolutely ",
    "it's ",
    "it is ",
    "its ",
    "mine is ",
    "that would be ",
    "that is ",
    "that's ",
    "i prefer ",
    "i use ",
    "i like ",
    "probably ",
    "honestly ",
)

NON_PERSONAL_QUESTION_PHRASES: tuple[str, ...] = (
    "write code",
    "write a function",
    "write a script",
    "this function",
    "this code",
    "fix this",
    "fix my code",
    "debug",
    "implement ",
    "how do i ",
    "how to ",
    "how does ",
    "how do ",
    "explain ",
    "describe ",
    "calculate",
    "solve ",
    "what is python",
    "what is javascript",
    "what is java",
    "what is rust",
    "what is c++",
    "what is recursion",
    "what is machine learning",
    "tell me about python",
    "tell me about javascript",
    "error ",
    "exception ",
    "bug ",
    "sort ",
    "function ",
    "algorithm ",
)

MATH_PATTERN = re.compile(r"\d\s*[\+\-\*/\^=]\s*\d")

PERSONAL_QUESTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"what(?:'s| is) your favorite (.+?)\??$", re.IGNORECASE),
        "My favorite {topic} is {value}.",
    ),
    (
        re.compile(r"what(?:'s| is) your name\??$", re.IGNORECASE),
        "My name is {value}.",
    ),
    (
        re.compile(r"where do you live\??$", re.IGNORECASE),
        "I live in {value}.",
    ),
    (
        re.compile(r"where are you from\??$", re.IGNORECASE),
        "I am from {value}.",
    ),
    (
        re.compile(r"what(?:'s| is) your goal\??$", re.IGNORECASE),
        "My goal is {value}.",
    ),
    (
        re.compile(r"what do you (?:like|love|enjoy)\??$", re.IGNORECASE),
        "I like {value}.",
    ),
    (
        re.compile(r"what(?:'s| is) your (.+?)\??$", re.IGNORECASE),
        "My {topic} is {value}.",
    ),
)

CONFIRMATION_PATTERN = re.compile(
    r"is (.+?) your favorite (.+?)\??$",
    re.IGNORECASE,
)

MAX_INFERRED_REPLY_WORDS = 8


@dataclass(frozen=True)
class ParsedPersonalQuestion:
    """A personal question parsed from the assistant message."""

    template: str
    topic: str = ""


def _contains_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    """Return True when any phrase appears in the text."""
    return any(phrase in text for phrase in phrases)


def _is_non_personal_question(text: str) -> bool:
    """Return True when the assistant question is not asking for personal info."""
    normalized = normalize_text(text)

    if _contains_phrase(normalized, NON_PERSONAL_QUESTION_PHRASES):
        return True

    if _contains_phrase(normalized, CODING_PHRASES):
        return True

    if MATH_PATTERN.search(normalized):
        return True

    if "your" not in normalized and not any(
        phrase in normalized
        for phrase in ("where do you live", "where are you from", "what do you like", "what do you love")
    ):
        return True

    return False


def is_personal_info_question(assistant_message: str) -> bool:
    """Return True when the assistant message asks for personal information."""
    if not assistant_message or not assistant_message.strip():
        return False

    normalized = normalize_text(assistant_message)
    if not normalized.endswith("?") and "?" not in assistant_message:
        return False

    if _is_non_personal_question(normalized):
        return False

    return parse_personal_question(assistant_message) is not None


def parse_personal_question(assistant_message: str) -> ParsedPersonalQuestion | None:
    """Parse a personal-information question into a memory template."""
    text = assistant_message.strip()
    normalized = normalize_text(text)

    if not normalized.endswith("?"):
        return None

    if _is_non_personal_question(normalized):
        return None

    confirmation = CONFIRMATION_PATTERN.match(text)
    if confirmation:
        topic = confirmation.group(2).strip(" ?.")
        return ParsedPersonalQuestion(
            template="My favorite {topic} is {value}.",
            topic=_clean_topic(topic),
        )

    for pattern, template in PERSONAL_QUESTION_PATTERNS:
        match = pattern.match(text)
        if not match:
            continue

        topic = ""
        if "{topic}" in template and match.lastindex and match.lastindex >= 1:
            topic = _clean_topic(match.group(1))

        if template == "My {topic} is {value}." and topic in {"favorite", "name", "goal"}:
            continue

        return ParsedPersonalQuestion(template=template, topic=topic)

    return None


def _clean_topic(topic: str) -> str:
    """Normalize a topic extracted from an assistant question."""
    cleaned = topic.strip(" ?.")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _format_memory_value(raw_value: str) -> str:
    """Format an extracted reply value for storage."""
    return raw_value.strip(" .!?")


def _extract_reply_value(user_message: str) -> str | None:
    """Extract the answer value from a short conversational reply."""
    original = user_message.strip()
    if not original:
        return None

    normalized = normalize_text(original)
    if _should_skip(normalized):
        return None

    if normalized in AFFIRMATIONS or normalized in NEGATIONS:
        return normalized

    working = normalized
    for prefix in REPLY_PREFIXES:
        if working.startswith(prefix):
            working = working[len(prefix) :].strip()
            break

    if not working or _should_skip(working):
        return None

    if len(working.split()) > MAX_INFERRED_REPLY_WORDS:
        return None

    if any(char in working for char in "+*/=(){}[]"):
        return None

    if _contains_phrase(working, CODING_PHRASES + EXPLANATION_PHRASES + JOKE_PHRASES):
        return None

    if any(working.startswith(starter) for starter in QUESTION_STARTERS):
        return None

    value = original
    if working != normalized:
        lowered_original = original.lower()
        for prefix in REPLY_PREFIXES:
            if lowered_original.startswith(prefix):
                value = original[len(prefix) :].strip()
                break

    return _format_memory_value(value)


def _build_memory_from_confirmation(
    parsed: ParsedPersonalQuestion,
    assistant_message: str,
) -> str | None:
    """Build a memory from a yes/no confirmation question."""
    match = CONFIRMATION_PATTERN.match(assistant_message.strip())
    if not match:
        return None

    value = _format_memory_value(match.group(1).strip())
    topic = _clean_topic(match.group(2))
    return parsed.template.format(topic=topic, value=value)


def infer_memory(user_message: str, previous_assistant_message: str | None) -> str | None:
    """Infer a memory statement from a conversational reply to a personal question."""
    if not previous_assistant_message:
        return None

    parsed = parse_personal_question(previous_assistant_message)
    if parsed is None:
        return None

    reply_value = _extract_reply_value(user_message)
    if reply_value is None:
        return None

    if reply_value in NEGATIONS:
        return None

    if reply_value in AFFIRMATIONS:
        return _build_memory_from_confirmation(parsed, previous_assistant_message)

    if parsed.template == "My favorite {topic} is {value}.":
        return parsed.template.format(topic=parsed.topic, value=reply_value)

    if "{topic}" in parsed.template:
        return parsed.template.format(topic=parsed.topic, value=reply_value)

    return parsed.template.format(value=reply_value)
