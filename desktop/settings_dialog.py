"""Settings dialog for Zoe Desktop."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config import ROOT, SETTINGS_FILE, load_settings
from desktop.preferences import DesktopPreferences
from voice.audio import list_input_devices, list_output_devices
from voice.settings import VoiceSettings

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Theme, paths, logging, and voice preferences."""

    def __init__(
        self,
        preferences: DesktopPreferences,
        parent=None,
        *,
        voice_settings: VoiceSettings | None = None,
    ) -> None:
        super().__init__(parent)
        self.preferences = preferences
        self.voice_settings = voice_settings or VoiceSettings.load()
        self.setWindowTitle("Zoe Settings")

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        general = QWidget()
        general_form = QFormLayout(general)
        self.theme = QComboBox()
        self.theme.addItems(["system", "dark", "light"])
        self.theme.setCurrentText(preferences.theme())
        general_form.addRow("Theme", self.theme)

        settings = load_settings()
        self.model_path = QLineEdit(settings.get("MODEL_NAME", ""))
        general_form.addRow("Model path", self.model_path)

        self.memory_db = QLineEdit(settings.get("MEMORY_DB", "storage/chroma"))
        general_form.addRow("Chroma path", self.memory_db)

        self.context_size = QSpinBox()
        self.context_size.setRange(1000, 20000)
        self.context_size.setValue(preferences.context_size())
        general_form.addRow("Context size", self.context_size)

        self.memory_limit = QSpinBox()
        self.memory_limit.setRange(5, 100)
        self.memory_limit.setValue(preferences.memory_limit())
        general_form.addRow("Memory message limit", self.memory_limit)

        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level.setCurrentText(preferences.log_level())
        general_form.addRow("Logging", self.log_level)

        self.notes_folder = QLineEdit(preferences.default_notes_folder())
        general_form.addRow("Notes folder", self.notes_folder)

        self.pdf_folder = QLineEdit(preferences.default_pdf_folder())
        general_form.addRow("PDF folder", self.pdf_folder)

        self.code_folder = QLineEdit(preferences.default_code_folder())
        general_form.addRow("Code folder", self.code_folder)
        tabs.addTab(general, "General")

        voice = QWidget()
        voice_form = QFormLayout(voice)
        from voice.deps import voice_capture_available, voice_install_hint, voice_tts_available

        if not voice_capture_available() or not voice_tts_available():
            voice_form.addRow(
                QLabel(
                    f"Optional voice packages not installed. Run: {voice_install_hint()}\n"
                    "Zoe works without them; microphone and TTS stay disabled until installed."
                )
            )

        self.voice_enabled = QCheckBox("Enable voice assistant")
        self.voice_enabled.setChecked(self.voice_settings.enabled)
        voice_form.addRow(self.voice_enabled)

        self.input_device = QComboBox()
        self.input_device.addItem("Default", "")
        if voice_capture_available():
            for device in list_input_devices():
                self.input_device.addItem(device.name, device.name)
        if self.voice_settings.input_device:
            index = self.input_device.findData(self.voice_settings.input_device)
            if index >= 0:
                self.input_device.setCurrentIndex(index)
        voice_form.addRow("Microphone", self.input_device)

        self.output_device = QComboBox()
        self.output_device.addItem("Default", "")
        try:
            if voice_tts_available():
                for device in list_output_devices():
                    self.output_device.addItem(device.name, device.name)
        except Exception as exc:
            # Optional TTS device enumeration — keep Default when unavailable.
            logger.debug("Output device enumeration skipped: %s", exc)
        if self.voice_settings.output_device:
            index = self.output_device.findData(self.voice_settings.output_device)
            if index >= 0:
                self.output_device.setCurrentIndex(index)
        voice_form.addRow("Speaker", self.output_device)

        self.speech_rate = QSpinBox()
        self.speech_rate.setRange(80, 300)
        self.speech_rate.setValue(self.voice_settings.speech_rate)
        voice_form.addRow("Speech rate", self.speech_rate)

        self.speech_volume = QDoubleSpinBox()
        self.speech_volume.setRange(0.0, 1.0)
        self.speech_volume.setSingleStep(0.05)
        self.speech_volume.setValue(self.voice_settings.speech_volume)
        voice_form.addRow("Speech volume", self.speech_volume)

        self.language = QComboBox()
        self.language.addItems(["en", "es", "fr", "de", "auto"])
        self.language.setCurrentText(self.voice_settings.language)
        voice_form.addRow("Recognition language", self.language)

        self.auto_speak = QCheckBox("Auto speak responses")
        self.auto_speak.setChecked(self.voice_settings.auto_speak)
        voice_form.addRow(self.auto_speak)

        self.silence_seconds = QDoubleSpinBox()
        self.silence_seconds.setRange(1.0, 6.0)
        self.silence_seconds.setSingleStep(0.5)
        self.silence_seconds.setValue(self.voice_settings.silence_seconds)
        voice_form.addRow("Auto stop after silence (s)", self.silence_seconds)

        self.noise_threshold = QDoubleSpinBox()
        self.noise_threshold.setRange(0.001, 0.2)
        self.noise_threshold.setSingleStep(0.001)
        self.noise_threshold.setValue(self.voice_settings.noise_threshold)
        voice_form.addRow("Noise threshold", self.noise_threshold)
        tabs.addTab(voice, "Voice")

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Reset | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset_defaults)
        layout.addWidget(buttons)

    def save(self) -> None:
        self.preferences.set_theme(self.theme.currentText())
        self.preferences.set_context_size(self.context_size.value())
        self.preferences.set_memory_limit(self.memory_limit.value())
        self.preferences.set_log_level(self.log_level.currentText())
        self.preferences.set_default_notes_folder(self.notes_folder.text().strip())
        self.preferences.set_default_pdf_folder(self.pdf_folder.text().strip())
        self.preferences.set_default_code_folder(self.code_folder.text().strip())

        self.voice_settings.enabled = self.voice_enabled.isChecked()
        self.voice_settings.input_device = str(self.input_device.currentData() or "")
        self.voice_settings.output_device = str(self.output_device.currentData() or "")
        self.voice_settings.speech_rate = self.speech_rate.value()
        self.voice_settings.speech_volume = float(self.speech_volume.value())
        self.voice_settings.language = self.language.currentText()
        self.voice_settings.auto_speak = self.auto_speak.isChecked()
        self.voice_settings.silence_seconds = float(self.silence_seconds.value())
        self.voice_settings.noise_threshold = float(self.noise_threshold.value())
        self.voice_settings.save()

        self._write_backend_settings()
        self.accept()

    def _write_backend_settings(self) -> None:
        current = load_settings()
        current["MODEL_NAME"] = self.model_path.text().strip()
        current["MEMORY_DB"] = self.memory_db.text().strip()
        lines = [f"{key}={value}" for key, value in current.items()]
        SETTINGS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def reset_defaults(self) -> None:
        self.theme.setCurrentText("system")
        self.context_size.setValue(6000)
        self.memory_limit.setValue(20)
        self.log_level.setCurrentText("INFO")
        self.notes_folder.setText("data/notes")
        self.pdf_folder.setText("data/pdfs")
        self.code_folder.setText(str(ROOT / "data" / "code"))
        self.voice_enabled.setChecked(False)
        self.speech_rate.setValue(180)
        self.speech_volume.setValue(1.0)
        self.language.setCurrentText("en")
        self.auto_speak.setChecked(True)
        self.silence_seconds.setValue(2.5)
        self.noise_threshold.setValue(0.015)
