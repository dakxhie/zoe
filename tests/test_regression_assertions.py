"""Unit tests for regression assertion helpers."""

from __future__ import annotations

import pytest

from tests.regression.assertions import (
    RegressionAssertionError,
    assert_contains,
    assert_equals,
    assert_not_empty,
)


def test_assert_equals_passes() -> None:
    assert_equals("a", "a")


def test_assert_equals_fails() -> None:
    with pytest.raises(RegressionAssertionError):
        assert_equals("a", "b")


def test_assert_contains_case_insensitive() -> None:
    assert_contains("Hello Wolf", "wolf")


def test_assert_not_empty_rejects_blank() -> None:
    with pytest.raises(RegressionAssertionError):
        assert_not_empty("   ")
