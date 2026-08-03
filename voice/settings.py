"""Voice configuration persisted via QSettings."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings

ORG = "ZoeAI"
APP = "Voice"


@dataclass
class VoiceSettings:
    """User-configurable voice options."""

    enabled: bool = False
    input_device: str = ""
    output_device: str = ""
    speech_rate: int = 180
    speech_volume: float = 1.0
    language: str = "en"
    auto_speak: bool = True
    silence_seconds: float = 2.5
    noise_threshold: float = 0.015
    voice_id: str = ""

    @classmethod
    def load(cls) -> VoiceSettings:
        settings = QSettings(ORG, APP)
        return cls(
            enabled=str(settings.value("enabled", "false")).lower() == "true",
            input_device=str(settings.value("input_device", "")),
            output_device=str(settings.value("output_device", "")),
            speech_rate=int(settings.value("speech_rate", 180)),
            speech_volume=float(settings.value("speech_volume", 1.0)),
            language=str(settings.value("language", "en")),
            auto_speak=str(settings.value("auto_speak", "true")).lower() == "true",
            silence_seconds=float(settings.value("silence_seconds", 2.5)),
            noise_threshold=float(settings.value("noise_threshold", 0.015)),
            voice_id=str(settings.value("voice_id", "")),
        )

    def save(self) -> None:
        settings = QSettings(ORG, APP)
        settings.setValue("enabled", "true" if self.enabled else "false")
        settings.setValue("input_device", self.input_device)
        settings.setValue("output_device", self.output_device)
        settings.setValue("speech_rate", self.speech_rate)
        settings.setValue("speech_volume", self.speech_volume)
        settings.setValue("language", self.language)
        settings.setValue("auto_speak", "true" if self.auto_speak else "false")
        settings.setValue("silence_seconds", self.silence_seconds)
        settings.setValue("noise_threshold", self.noise_threshold)
        settings.setValue("voice_id", self.voice_id)
