"""Pytest coverage for calculator and datetime tools."""

from __future__ import annotations

from datetime import datetime

import pytest

from tools.calculator import calculate, is_calculator_request
from tools.datetime_tool import get_datetime_response, is_datetime_request
from tools.timezones import extract_timezone_query, resolve_timezone

TIMEZONE_CASES: tuple[tuple[str, str], ...] = (
    ("What time is it in India?", "Asia/Kolkata"),
    ("Time in Tokyo", "Asia/Tokyo"),
    ("Current time in London", "Europe/London"),
    ("Date in Japan", "Asia/Tokyo"),
    ("UTC time", "UTC"),
    ("IST time", "Asia/Kolkata"),
    ("PST time", "America/Los_Angeles"),
    ("EST time", "America/New_York"),
)


@pytest.mark.parametrize(("query", "expected_zone"), TIMEZONE_CASES)
def test_timezone_queries_are_detected(query: str, expected_zone: str) -> None:
    """Detect location and abbreviation based time requests."""
    assert is_datetime_request(query)
    parsed = extract_timezone_query(query)
    assert parsed is not None
    _kind, zone = parsed
    assert zone.key == expected_zone


@pytest.mark.parametrize(("query", "expected_zone"), TIMEZONE_CASES)
def test_timezone_responses_include_location(query: str, expected_zone: str) -> None:
    """Return a formatted response for timezone-aware requests."""
    response = get_datetime_response(query)
    assert response is not None
    assert "(" in response


def test_resolve_timezone_supports_country_and_iana_names() -> None:
    """Resolve countries, cities, abbreviations, and IANA names."""
    assert resolve_timezone("India").key == "Asia/Kolkata"
    assert resolve_timezone("Asia/Tokyo").key == "Asia/Tokyo"
    assert resolve_timezone("IST").key == "Asia/Kolkata"


def test_timezone_fallback_to_local_for_basic_requests() -> None:
    """Keep local date and time behavior unchanged."""
    assert is_datetime_request("Current time")
    assert is_datetime_request("Today's date")
    assert get_datetime_response("Current time")
    assert get_datetime_response("Today's date")


def test_unknown_timezone_returns_none() -> None:
    """Return None when a timezone cannot be resolved."""
    assert extract_timezone_query("What time is it in Atlantis?") is None
    assert get_datetime_response("What time is it in Atlantis?") is None


def test_calculator_basic_expression() -> None:
    """Evaluate a simple arithmetic expression."""
    assert calculate("2+2") == "4"
    assert is_calculator_request("10*(5+2)")


def test_calculator_rejects_non_math() -> None:
    """Ignore non-calculator queries."""
    assert not is_calculator_request("Hello")


def test_timezone_response_uses_zone_clock() -> None:
    """Format time using the resolved timezone."""
    parsed = extract_timezone_query("UTC time")
    assert parsed is not None
    kind, zone = parsed
    assert kind == "time"
    expected = datetime.now(zone).strftime("%I:%M %p").lstrip("0")
    assert expected in get_datetime_response("UTC time")
