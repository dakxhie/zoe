"""Offline text-to-speech using pyttsx3."""

from __future__ import annotations

import logging
import queue
import threading

from voice.utils import debug_timer

logger = logging.getLogger(__name__)

_engine = None
_engine_lock = threading.Lock()


class SpeechSpeaker:
    """Queued speech synthesis with interrupt support."""

    def __init__(self, *, rate: int = 180, volume: float = 1.0, voice_id: str = "") -> None:
        self._rate = rate
        self._volume = max(0.0, min(volume, 1.0))
        self.voice_id = voice_id
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _get_engine(self):
        global _engine
        with _engine_lock:
            if _engine is None:
                import pyttsx3

                _engine = pyttsx3.init()
                logger.info("pyttsx3 engine initialized")
            engine = _engine
        engine.setProperty("rate", self._rate)
        engine.setProperty("volume", self._volume)
        if self.voice_id:
            engine.setProperty("voice", self.voice_id)
        return engine

    @property
    def rate(self) -> int:
        return self._rate

    @rate.setter
    def rate(self, value: int) -> None:
        self._rate = value

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = max(0.0, min(value, 1.0))

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        from voice.deps import voice_tts_available

        if not voice_tts_available():
            logger.warning("TTS unavailable; install pyttsx3 via requirements-voice.txt")
            return
        self._queue.put(text)

    def cancel(self) -> None:
        self._stop_event.set()
        try:
            self._get_engine().stop()
        except Exception as exc:
            logger.debug("TTS stop: %s", exc)
        with self._queue.mutex:
            self._queue.queue.clear()
        self._stop_event.clear()

    def _run(self) -> None:
        while True:
            text = self._queue.get()
            if text is None:
                break
            if self._stop_event.is_set():
                continue
            try:
                engine = self._get_engine()
                with debug_timer("TTS speech"):
                    engine.say(text)
                    engine.runAndWait()
            except Exception as exc:
                logger.warning("TTS failure: %s", exc)
