"""Filters for trivial or ephemeral content that should not be stored."""

from __future__ import annotations

import logging
import re

from core.text_utils import matches_any, normalize_text
from tools.calculator import is_calculator_request
from tools.datetime_tool import is_datetime_request

logger = logging.getLogger(__name__)

SMALL_TALK: tuple[str, ...] = (
    "hello",
    "hi",
    "hey",
    "thanks",
    "thank you",
    "bye",
    "goodbye",
    "see you",
    "good morning",
    "good night",
    "how are you",
    "nice to meet you",
)

WEATHER_PHRASES: tuple[str, ...] = (
    "weather",
    "forecast",
    "temperature outside",
    "is it raining",
)

MATH_PATTERN = re.compile(r"^\s*[\d\s+\-*/().]+\s*$")

EXPLICIT_REMEMBER_MARKERS: tuple[str, ...] = (
    "remember this",
    "remember that",
    "don't forget",
    "do not forget",
    "save this",
    "keep in mind",
)


def is_explicit_remember_request(text: str) -> bool:
    normalized = normalize_text(text)
    return matches_any(normalized, EXPLICIT_REMEMBER_MARKERS)


def should_forget(text: str, *, route_hint: str = "") -> bool:
    """
    Return True when the message should not enter long-term memory.

    Explicit remember markers override forgetting.
    """
    if is_explicit_remember_request(text):
        return False

    normalized = normalize_text(text)
    if not normalized:
        return True

    if normalized in SMALL_TALK or any(
        normalized == phrase or normalized.startswith(f"{phrase} ")
        for phrase in SMALL_TALK
    ):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Ignored trivial memory: small talk")
        return True

    if matches_any(normalized, WEATHER_PHRASES):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Ignored trivial memory: weather")
        return True

    if is_calculator_request(text) or is_datetime_request(text):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Ignored trivial memory: calculator/datetime")
        return True

    if route_hint in {"calculator", "datetime", "filesystem"}:
        return True

    if MATH_PATTERN.match(normalized):
        return True

    return False
