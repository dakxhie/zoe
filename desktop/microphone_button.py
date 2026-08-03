"""Animated microphone button for voice states."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QPushButton

from voice.manager import VoiceState

STATE_COLORS = {
    VoiceState.IDLE.value: "#6b7280",
    VoiceState.LISTENING.value: "#2563eb",
    VoiceState.RECOGNIZING.value: "#2563eb",
    VoiceState.THINKING.value: "#ea580c",
    VoiceState.SPEAKING.value: "#16a34a",
    VoiceState.MUTED.value: "#6b7280",
    VoiceState.ERROR.value: "#dc2626",
}


class MicrophoneButton(QPushButton):
    """Push-to-talk microphone control."""

    push_to_talk = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("🎤 Voice", parent)
        self.setObjectName("secondary")
        self._state = VoiceState.IDLE.value
        self._pulse = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self.clicked.connect(self.push_to_talk.emit)
        self.set_state(VoiceState.IDLE.value)

    def set_state(self, state: str) -> None:
        self._state = state
        color = STATE_COLORS.get(state, STATE_COLORS[VoiceState.IDLE.value])
        self.setStyleSheet(f"background-color: {color}; color: white; border-radius: 8px; padding: 8px 14px;")
        if state == VoiceState.LISTENING.value:
            self._timer.start(250)
        else:
            self._timer.stop()
            self._pulse = 0

    def _animate(self) -> None:
        self._pulse = 1 - self._pulse
        alpha = 0.85 if self._pulse else 1.0
        color = STATE_COLORS[VoiceState.LISTENING.value]
        self.setStyleSheet(
            f"background-color: {color}; color: white; border-radius: 8px; padding: 8px 14px; opacity: {alpha};"
        )
