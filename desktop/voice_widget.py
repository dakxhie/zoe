"""Voice status widget for Zoe Desktop."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from desktop.microphone_button import MicrophoneButton


class VoiceWidget(QWidget):
    """Compact voice controls and state indicator."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Voice: idle")
        self.status_label.setStyleSheet("color: #94a3b8;")
        layout.addWidget(self.status_label)

        self.mic_button = MicrophoneButton()
        layout.addWidget(self.mic_button)

    def set_state(self, state: str) -> None:
        self.status_label.setText(f"Voice: {state}")
        self.mic_button.set_state(state)

    @property
    def microphone(self) -> MicrophoneButton:
        return self.mic_button
