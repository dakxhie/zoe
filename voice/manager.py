"""Voice pipeline manager for Zoe AI."""

from __future__ import annotations

import logging
import threading
import time
from enum import Enum

from PySide6.QtCore import QObject, QThread, Signal

from voice.audio import list_input_devices, list_output_devices
from voice.commands import VoiceAction, generate_voice_response, try_voice_command
from voice.listener import AudioListener
from voice.recognizer import RecognitionResult, transcribe
from voice.settings import VoiceSettings
from voice.speaker import SpeechSpeaker
from voice.utils import debug_timer

logger = logging.getLogger(__name__)


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    RECOGNIZING = "recognizing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    MUTED = "muted"
    ERROR = "error"


class _ListenThread(QThread):
    finished_capture = Signal(object)
    failed = Signal(str)

    def __init__(self, listener: AudioListener) -> None:
        super().__init__()
        self.listener = listener

    def run(self) -> None:
        try:
            self.finished_capture.emit(self.listener.record_until_silence())
        except Exception as exc:
            self.failed.emit(str(exc))


class _ThinkThread(QThread):
    finished_text = Signal(str)
    failed = Signal(str)
    desktop_action = Signal(object)

    def __init__(self, transcript: str, prepare_session=None) -> None:
        super().__init__()
        self.transcript = transcript
        self.prepare_session = prepare_session

    def run(self) -> None:
        try:
            command = try_voice_command(self.transcript)
            if command.handled:
                if command.action is not None:
                    self.desktop_action.emit(command.action)
                self.finished_text.emit(command.response)
                return
            if self.prepare_session:
                self.prepare_session()
            with debug_timer("Voice thinking (brain.pipeline)"):
                reply = generate_voice_response(self.transcript)
            self.finished_text.emit(reply)
        except Exception as exc:
            self.failed.emit(str(exc))


class VoiceManager(QObject):
    """Orchestrates listen → recognize → think → speak."""

    state_changed = Signal(str)
    transcript_ready = Signal(str, float)
    response_ready = Signal(str)
    error_occurred = Signal(str)
    desktop_action_requested = Signal(object)

    def __init__(self, settings: VoiceSettings | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings or VoiceSettings.load()
        self.state = VoiceState.IDLE
        self._prepare_session = None
        self._speaker = SpeechSpeaker(
            rate=self.settings.speech_rate,
            volume=self.settings.speech_volume,
            voice_id=self.settings.voice_id,
        )
        self._listener: AudioListener | None = None
        self._listen_thread: _ListenThread | None = None
        self._think_thread: _ThinkThread | None = None
        self._lock = threading.Lock()
        self._whisper_warmed = False

    def set_prepare_session(self, callback) -> None:
        """Register chat session initialization (same as desktop first message)."""
        self._prepare_session = callback

    def refresh_settings(self, settings: VoiceSettings) -> None:
        self.settings = settings
        self._speaker.rate = settings.speech_rate
        self._speaker.volume = settings.speech_volume
        self._speaker.voice_id = settings.voice_id

    def initialize_devices(self) -> tuple[list[str], list[str]]:
        inputs = [device.name for device in list_input_devices()]
        outputs = [device.name for device in list_output_devices()]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Voice input devices: %s", inputs)
            logger.debug("Voice output devices: %s", outputs)
        return inputs, outputs

    def _set_state(self, state: VoiceState) -> None:
        self.state = state
        self.state_changed.emit(state.value)

    def mute(self) -> None:
        self._speaker.cancel()
        self._set_state(VoiceState.MUTED)

    def resume(self) -> None:
        if self.state == VoiceState.MUTED:
            self._set_state(VoiceState.IDLE)

    def cancel_speech(self) -> None:
        self._speaker.cancel()
        if self._listener:
            self._listener.stop()
        self._set_state(VoiceState.IDLE)

    def start_listening(self) -> None:
        if not self.settings.enabled:
            self.error_occurred.emit("Voice is disabled in settings.")
            return
        from voice.deps import voice_capture_available, voice_install_hint

        if not voice_capture_available():
            self.error_occurred.emit(
                f"Microphone capture unavailable. Install optional voice packages: {voice_install_hint()}"
            )
            self._set_state(VoiceState.ERROR)
            self._set_state(VoiceState.IDLE)
            return
        if self.state in {VoiceState.LISTENING, VoiceState.RECOGNIZING, VoiceState.THINKING}:
            return
        if self.state == VoiceState.SPEAKING:
            self.cancel_speech()

        self._ensure_whisper_lazy()
        self._listener = AudioListener(
            silence_seconds=self.settings.silence_seconds,
            noise_threshold=self.settings.noise_threshold,
            input_device=self.settings.input_device,
        )
        self._set_state(VoiceState.LISTENING)
        self._listen_thread = _ListenThread(self._listener)
        self._listen_thread.finished_capture.connect(self._on_capture_complete)
        self._listen_thread.failed.connect(self._on_listen_failed)
        self._listen_thread.start()

    def _ensure_whisper_lazy(self) -> None:
        if self._whisper_warmed:
            return

        def _warm() -> None:
            try:
                from voice.recognizer import _load_whisper_model

                _load_whisper_model()
            except Exception as exc:
                logger.warning("Whisper preload skipped: %s", exc)

        threading.Thread(target=_warm, daemon=True).start()
        self._whisper_warmed = True

    def _on_listen_failed(self, message: str) -> None:
        self._set_state(VoiceState.ERROR)
        self.error_occurred.emit(message)
        self._set_state(VoiceState.IDLE)

    def _on_capture_complete(self, capture) -> None:
        self._set_state(VoiceState.RECOGNIZING)
        from voice.deps import voice_stt_available, voice_install_hint

        if not voice_stt_available():
            self.error_occurred.emit(
                f"Speech recognition unavailable. Install optional voice packages: {voice_install_hint()}"
            )
            self._set_state(VoiceState.IDLE)
            return
        try:
            with debug_timer("Speech recognition total"):
                result: RecognitionResult = transcribe(
                    capture.samples,
                    capture.sample_rate,
                    self.settings.language,
                )
        except Exception as exc:
            self._set_state(VoiceState.ERROR)
            self.error_occurred.emit(str(exc))
            self._set_state(VoiceState.IDLE)
            return

        if not result.text.strip():
            self.error_occurred.emit("No speech detected.")
            self._set_state(VoiceState.IDLE)
            return

        self.transcript_ready.emit(result.text, result.confidence)
        self._think(result.text)

    def _think(self, transcript: str) -> None:
        self._set_state(VoiceState.THINKING)
        self._think_thread = _ThinkThread(transcript, self._prepare_session)
        self._think_thread.finished_text.connect(self._on_response)
        self._think_thread.failed.connect(self._on_think_failed)
        self._think_thread.desktop_action.connect(self.desktop_action_requested.emit)
        self._think_thread.start()

    def _on_think_failed(self, message: str) -> None:
        self._set_state(VoiceState.ERROR)
        self.error_occurred.emit(message)
        self._set_state(VoiceState.IDLE)

    def _on_response(self, response: str) -> None:
        self.response_ready.emit(response)
        if self.settings.auto_speak and response.strip():
            self.speak(response)
        else:
            self._set_state(VoiceState.IDLE)

    def speak(self, text: str) -> None:
        if self.state == VoiceState.MUTED:
            return
        from voice.deps import voice_tts_available

        if not voice_tts_available():
            self._set_state(VoiceState.IDLE)
            return
        self._set_state(VoiceState.SPEAKING)

        def _run() -> None:
            start = time.perf_counter()
            self._speaker.speak(text)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Speech duration %.2fs", time.perf_counter() - start)
            self._set_state(VoiceState.IDLE)

        threading.Thread(target=_run, daemon=True).start()

    def toggle_push_to_talk(self) -> None:
        if self.state == VoiceState.LISTENING:
            if self._listener:
                self._listener.stop()
        else:
            self.start_listening()
