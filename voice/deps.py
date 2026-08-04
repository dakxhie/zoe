"""Optional voice dependency detection (no imports of heavy voice stack)."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceDependencyStatus:
    """Availability of optional voice components."""

    capture: bool
    stt: bool
    tts: bool
    missing: tuple[str, ...]

    @property
    def fully_available(self) -> bool:
        return self.capture and self.stt and self.tts

    @property
    def partially_available(self) -> bool:
        return self.capture or self.stt or self.tts


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def voice_dependency_status() -> VoiceDependencyStatus:
    """Report which optional voice packages are installed."""
    missing: list[str] = []

    capture = _has_module("sounddevice")
    if not capture:
        missing.append("sounddevice (microphone capture)")

    has_whisper = _has_module("whisper")
    has_sr = _has_module("speech_recognition")
    stt = has_whisper or has_sr
    if not has_whisper and not has_sr:
        missing.append("STT (openai-whisper or SpeechRecognition)")

    tts = _has_module("pyttsx3")
    if not tts:
        missing.append("pyttsx3 (text-to-speech)")

    return VoiceDependencyStatus(
        capture=capture,
        stt=stt,
        tts=tts,
        missing=tuple(missing),
    )


def voice_capture_available() -> bool:
    """Return True when sounddevice capture is available."""
    return _has_module("sounddevice")


def voice_stt_available() -> bool:
    """Return True when at least one STT backend is available."""
    return _has_module("whisper") or _has_module("speech_recognition")


def voice_tts_available() -> bool:
    """Return True when offline TTS is available."""
    return _has_module("pyttsx3")


def voice_install_hint() -> str:
    return "pip install -r requirements-voice.txt"
