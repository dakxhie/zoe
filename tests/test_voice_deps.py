"""Tests for optional voice dependency detection."""

from __future__ import annotations

from unittest.mock import patch

from voice.deps import (
    voice_capture_available,
    voice_dependency_status,
    voice_install_hint,
    voice_stt_available,
    voice_tts_available,
)


def test_voice_install_hint_points_to_optional_requirements() -> None:
    assert "requirements-voice.txt" in voice_install_hint()


@patch("voice.deps._has_module", return_value=False)
def test_missing_voice_packages_reported(_mock_has) -> None:
    status = voice_dependency_status()
    assert status.fully_available is False
    assert status.missing


@patch("voice.deps._has_module")
def test_full_voice_stack_detected(mock_has) -> None:
    mock_has.side_effect = lambda name: name in {"sounddevice", "whisper", "pyttsx3"}
    assert voice_capture_available()
    assert voice_stt_available()
    assert voice_tts_available()
    assert voice_dependency_status().fully_available
