"""Speaker tests."""

from __future__ import annotations

from voice.speaker import SpeechSpeaker


def test_speaker_queue_accepts_text() -> None:
    speaker = SpeechSpeaker(rate=180, volume=0.5)
    speaker.speak("test")
    speaker.cancel()
