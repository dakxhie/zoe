"""Recognizer tests."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np

from voice.recognizer import RecognitionResult, transcribe


def test_transcribe_empty_audio() -> None:
    with patch("voice.recognizer.transcribe_whisper") as mock_whisper:
        mock_whisper.return_value = RecognitionResult("", 0.0, "en", 0.0)
        result = transcribe(np.array([], dtype=np.float32), 16000, "en")
    assert result.text == ""


def test_transcribe_whisper_success() -> None:
    samples = np.zeros(16000, dtype=np.float32)
    with patch("voice.recognizer.transcribe_whisper") as mock_whisper:
        mock_whisper.return_value = RecognitionResult("hello", 0.9, "en", 1.0)
        result = transcribe(samples, 16000, "en")
    assert result.text == "hello"
    assert result.confidence == 0.9
