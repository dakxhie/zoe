"""Local date and time responses."""

from __future__ import annotations

from datetime import datetime

from core.text_utils import matches_any, normalize_text

TIME_PHRASES: tuple[str, ...] = (
    "what time is it",
    "current time",
)

DATE_PHRASES: tuple[str, ...] = (
    "today's date",
    "todays date",
    "what day is today",
)


def is_datetime_request(query: str) -> bool:
    """Return True when the query asks for the current date or time."""
    normalized = normalize_text(query)
    return matches_any(normalized, (*TIME_PHRASES, *DATE_PHRASES))


def get_datetime_response(query: str) -> str | None:
    """Return a local date or time response when the query matches."""
    normalized = normalize_text(query)
    now = datetime.now()

    if any(phrase in normalized for phrase in TIME_PHRASES):
        return now.strftime("%I:%M %p").lstrip("0")

    if any(phrase in normalized for phrase in DATE_PHRASES):
        return now.strftime("%A, %B %d, %Y")

    return None
