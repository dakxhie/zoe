"""Forgetting filter tests (not executed in sprint)."""

from __future__ import annotations

from memory.intelligence.forgetting import is_explicit_remember_request, should_forget


def test_small_talk_forgotten() -> None:
    assert should_forget("hello")
    assert should_forget("thanks")


def test_weather_forgotten() -> None:
    assert should_forget("what is the weather today")


def test_explicit_remember_overrides() -> None:
    assert is_explicit_remember_request("remember this: my dog is Max")
    assert not should_forget("remember this: my dog is Max")


def test_calculator_forgotten() -> None:
    assert should_forget("what is 2+2")
