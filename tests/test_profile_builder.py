"""User profile builder tests (not executed in sprint)."""

from __future__ import annotations

from memory.intelligence.profile_builder import (
    build_user_profile,
    format_profile_summary_for_user,
    is_learned_summary_query,
    is_profile_summary_query,
)


def test_profile_summary_query_detection() -> None:
    assert is_profile_summary_query("What do you know about me?")
    assert is_learned_summary_query("What have you learned?")


def test_build_profile_from_records() -> None:
    profile = build_user_profile(
        [
            {"text": "My name is Dakshitha.", "category": "identity", "importance": "0.95"},
            {"text": "I live in India.", "category": "semantic", "importance": "0.7"},
            {"text": "I am building Zoe AI.", "category": "project", "importance": "0.9"},
        ]
    )
    assert profile.name == "Dakshitha"
    assert profile.location == "India"
    assert "Zoe AI" in profile.projects[0]


def test_format_profile_for_user() -> None:
    profile = build_user_profile([{"text": "My name is Alex.", "category": "identity"}])
    text = format_profile_summary_for_user(profile)
    assert "Alex" in text
    assert "learned" in text.lower()
