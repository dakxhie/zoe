"""End-to-end voice pipeline tests (mocked audio)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from tests.headless import skip_if_headless_gui

skip_if_headless_gui()

pytest.importorskip("PySide6")

from voice.listener import CaptureResult
from voice.manager import VoiceManager
from voice.recognizer import RecognitionResult
from voice.settings import VoiceSettings


@patch("voice.deps.voice_stt_available", return_value=True)
def test_capture_to_response_pipeline(_mock_stt, qapp) -> None:
    settings = VoiceSettings(enabled=True, auto_speak=False)
    manager = VoiceManager(settings)
    manager.set_prepare_session(lambda: None)

    capture = CaptureResult(np.ones(16000, dtype=np.float32), 16000, 1.0)
    recognition = RecognitionResult("hello zoe", 0.8, "en", 1.0)

    with patch("voice.manager.transcribe", return_value=recognition), patch(
        "voice.manager.generate_voice_response",
        return_value="Hi there",
    ):
        responses: list[str] = []
        manager.response_ready.connect(responses.append)
        manager._on_capture_complete(capture)

    assert responses == ["Hi there"]
