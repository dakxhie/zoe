"""Timezone resolution helpers for Zoe AI."""

from __future__ import annotations

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TIMEZONE_ALIASES: dict[str, str] = {
    "utc": "UTC",
    "gmt": "UTC",
    "ist": "Asia/Kolkata",
    "pst": "America/Los_Angeles",
    "pdt": "America/Los_Angeles",
    "est": "America/New_York",
    "edt": "America/New_York",
    "cst": "America/Chicago",
    "cdt": "America/Chicago",
    "mst": "America/Denver",
    "mdt": "America/Denver",
    "jst": "Asia/Tokyo",
    "cet": "Europe/Paris",
    "bst": "Europe/London",
}

LOCATION_ALIASES: dict[str, str] = {
    "india": "Asia/Kolkata",
    "japan": "Asia/Tokyo",
    "tokyo": "Asia/Tokyo",
    "london": "Europe/London",
    "uk": "Europe/London",
    "united kingdom": "Europe/London",
    "new york": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "sydney": "Australia/Sydney",
    "singapore": "Asia/Singapore",
    "dubai": "Asia/Dubai",
    "utc": "UTC",
}

TIME_LOCATION_PATTERN = re.compile(
    r"(?:what time is it in|current time in|time in|time at)\s+(?P<location>.+?)(?:\?|$)",
    re.IGNORECASE,
)
DATE_LOCATION_PATTERN = re.compile(
    r"(?:today'?s date in|date in|what(?:'s| is) the date in)\s+(?P<location>.+?)(?:\?|$)",
    re.IGNORECASE,
)
ABBREV_TIME_PATTERN = re.compile(
    r"\b(?P<abbrev>utc|gmt|ist|pst|pdt|est|edt|cst|cdt|mst|mdt|jst|cet|bst)\s+time\b",
    re.IGNORECASE,
)
LOCATION_TIME_PATTERN = re.compile(
    r"\btime in\s+(?P<location>[a-zA-Z /]+)\b",
    re.IGNORECASE,
)


def _clean_location(value: str) -> str:
    """Normalize a location or timezone token from user input."""
    cleaned = value.strip(" ?.!")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def resolve_timezone(location: str) -> ZoneInfo | None:
    """Resolve a country, city, abbreviation, or IANA timezone name."""
    cleaned = _clean_location(location)
    if not cleaned:
        return None

    lowered = cleaned.lower()
    if lowered in TIMEZONE_ALIASES:
        return _safe_zone(TIMEZONE_ALIASES[lowered])

    if lowered in LOCATION_ALIASES:
        return _safe_zone(LOCATION_ALIASES[lowered])

    if "/" in cleaned:
        return _safe_zone(cleaned)

    return _safe_zone(cleaned.replace(" ", "_"))


def _safe_zone(name: str) -> ZoneInfo | None:
    """Return ZoneInfo when valid, otherwise None."""
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return None


def extract_timezone_query(query: str) -> tuple[str, ZoneInfo] | None:
    """Extract a timezone and request kind ('time' or 'date') from a query."""
    normalized = query.strip()

    match = TIME_LOCATION_PATTERN.search(normalized)
    if match:
        zone = resolve_timezone(match.group("location"))
        if zone is not None:
            return "time", zone

    match = DATE_LOCATION_PATTERN.search(normalized)
    if match:
        zone = resolve_timezone(match.group("location"))
        if zone is not None:
            return "date", zone

    match = ABBREV_TIME_PATTERN.search(normalized)
    if match:
        zone = resolve_timezone(match.group("abbrev"))
        if zone is not None:
            return "time", zone

    match = LOCATION_TIME_PATTERN.search(normalized)
    if match:
        zone = resolve_timezone(match.group("location"))
        if zone is not None:
            return "time", zone

    lowered = normalized.lower()
    for abbrev in TIMEZONE_ALIASES:
        if re.search(rf"\b{abbrev}\b", lowered) and "time" in lowered:
            zone = resolve_timezone(abbrev)
            if zone is not None:
                return "time", zone

    return None
