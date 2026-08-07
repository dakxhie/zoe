"""Local date and time responses."""

from __future__ import annotations

from datetime import datetime

from core.text_utils import matches_any, normalize_text
from tools.timezones import extract_timezone_query, is_location_datetime_query

TIME_PHRASES: tuple[str, ...] = (
    "what time is it",
    "current time",
    "time now",
)

DATE_PHRASES: tuple[str, ...] = (
    "today's date",
    "todays date",
    "what day is today",
    "current date",
)


def is_datetime_request(query: str) -> bool:
    """Return True when the query asks for the current date or time."""
    normalized = normalize_text(query)
    if extract_timezone_query(query) is not None:
        return True
    return matches_any(normalized, (*TIME_PHRASES, *DATE_PHRASES))


def _format_timezone_label(zone_name: str) -> str:
    """Return a readable timezone label."""
    return zone_name.replace("_", " ")


def get_datetime_response(query: str) -> str | None:
    """Return a local or location-based date or time response when the query matches."""
    timezone_query = extract_timezone_query(query)
    if timezone_query is not None:
        request_kind, zone = timezone_query
        now = datetime.now(zone)
        label = _format_timezone_label(getattr(zone, "key", str(zone)))

        if request_kind == "date":
            return now.strftime(f"%A, %B %d, %Y ({label})")

        return now.strftime(f"%I:%M %p ({label})").lstrip("0")

    if is_location_datetime_query(query):
        return None

    normalized = normalize_text(query)
    now = datetime.now()

    if any(phrase in normalized for phrase in TIME_PHRASES):
        return now.strftime("%I:%M %p").lstrip("0")

    if any(phrase in normalized for phrase in DATE_PHRASES):
        return now.strftime("%A, %B %d, %Y")

    return None
