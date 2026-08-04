"""Reusable assertion helpers for regression scenarios."""

from __future__ import annotations

from typing import Any, Iterable


class RegressionAssertionError(AssertionError):
    """Assertion failure during a regression scenario."""


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionAssertionError(message)


def assert_equals(actual: Any, expected: Any, message: str | None = None) -> None:
    if actual != expected:
        detail = message or f"Expected {expected!r}, got {actual!r}"
        raise RegressionAssertionError(detail)


def assert_not_empty(value: str | list | dict | None, message: str = "Expected non-empty value") -> None:
    if value is None:
        raise RegressionAssertionError(message)
    if isinstance(value, str) and not value.strip():
        raise RegressionAssertionError(message)
    if isinstance(value, (list, dict)) and len(value) == 0:
        raise RegressionAssertionError(message)


def assert_contains(haystack: str, needle: str, message: str | None = None) -> None:
    if needle.lower() not in haystack.lower():
        detail = message or f"Expected text to contain {needle!r}"
        raise RegressionAssertionError(detail)


def assert_contains_any(haystack: str, needles: Iterable[str], message: str | None = None) -> None:
    lowered = haystack.lower()
    if not any(needle.lower() in lowered for needle in needles):
        detail = message or f"Expected text to contain one of {list(needles)!r}"
        raise RegressionAssertionError(detail)


def assert_pass(condition: bool, pass_message: str, fail_message: str) -> None:
    if not condition:
        raise RegressionAssertionError(fail_message or pass_message)


def assert_collection_exists(collection_names: Iterable[str], name: str, message: str | None = None) -> None:
    normalized = {item.lower() for item in collection_names}
    if name.lower() not in normalized:
        detail = message or f"Collection {name!r} was not found"
        raise RegressionAssertionError(detail)
