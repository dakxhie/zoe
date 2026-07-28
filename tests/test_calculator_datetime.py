"""Pytest coverage for calculator and datetime tools."""

from __future__ import annotations

from tools.calculator import calculate, is_calculator_request
from tools.datetime_tool import get_datetime_response, is_datetime_request


def test_calculator_basic_expression() -> None:
    """Evaluate a simple arithmetic expression."""
    assert calculate("2+2") == "4"
    assert is_calculator_request("10*(5+2)")


def test_calculator_rejects_non_math() -> None:
    """Ignore non-calculator queries."""
    assert not is_calculator_request("Hello")


def test_datetime_time_request() -> None:
    """Return a time string for time queries."""
    assert is_datetime_request("Current time")
    assert get_datetime_response("Current time")


def test_datetime_date_request() -> None:
    """Return a date string for date queries."""
    assert is_datetime_request("Today's date")
    assert get_datetime_response("Today's date")
