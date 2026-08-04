"""Speaker tests."""

from __future__ import annotations

import pytest

from voice.deps import voice_tts_available


@pytest.mark.voice_optional
def test_speaker_queue_accepts_text() -> None:
    if not voice_tts_available():
        pytest.skip("Optional voice dependencies not installed")

    from voice.speaker import SpeechSpeaker

    speaker = SpeechSpeaker(rate=180, volume=0.5)
    speaker.speak("test")
    speaker.cancel()
