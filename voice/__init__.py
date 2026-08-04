"""Voice assistant package for Zoe AI."""

from __future__ import annotations

from typing import Any

__all__ = ["VoiceManager", "VoiceSettings", "VoiceState"]


def __getattr__(name: str) -> Any:
    if name in {"VoiceManager", "VoiceState"}:
        from voice.manager import VoiceManager, VoiceState

        return VoiceManager if name == "VoiceManager" else VoiceState
    if name == "VoiceSettings":
        from voice.settings import VoiceSettings

        return VoiceSettings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
