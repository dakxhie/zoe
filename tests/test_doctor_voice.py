"""Doctor voice check tests."""

from __future__ import annotations

from unittest.mock import patch

from core.doctor import CheckStatus, check_voice


def test_check_voice_warns_when_optional_deps_missing() -> None:
    with patch("voice.deps.voice_dependency_status") as mock_status, patch(
        "voice.deps.voice_capture_available",
        return_value=False,
    ), patch("voice.deps.voice_stt_available", return_value=False), patch(
        "voice.deps.voice_tts_available",
        return_value=False,
    ), patch("voice.deps.voice_install_hint", return_value="pip install -r requirements-voice.txt"):
        mock_status.return_value = type(
            "S",
            (),
            {"fully_available": False, "missing": ("sounddevice",)},
        )()
        result = check_voice()

    assert result.name == "Voice"
    assert result.status == CheckStatus.WARN
    assert result.status != CheckStatus.FAIL


def test_check_voice_passes_when_deps_installed() -> None:
    with patch("voice.deps.voice_dependency_status") as mock_status, patch(
        "voice.deps.voice_capture_available",
        return_value=True,
    ), patch("voice.deps.voice_stt_available", return_value=True), patch(
        "voice.deps.voice_tts_available",
        return_value=True,
    ):
        mock_status.return_value = type("S", (), {"fully_available": True, "missing": ()})()
        result = check_voice()

    assert result.status == CheckStatus.PASS
