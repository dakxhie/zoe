"""Speech-to-text using Whisper with SpeechRecognition fallback."""

from __future__ import annotations

import io
import logging
import tempfile
import wave
from dataclasses import dataclass

import numpy as np

from voice.utils import debug_timer, normalize_transcript

logger = logging.getLogger(__name__)

_whisper_model = None


@dataclass(frozen=True)
class RecognitionResult:
    """Transcription output."""

    text: str
    confidence: float
    language: str
    duration: float


def _samples_to_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    pcm = np.clip(samples, -1.0, 1.0)
    pcm16 = (pcm * 32767).astype(np.int16)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm16.tobytes())
    return buffer.getvalue()


def _load_whisper_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    import whisper

    _whisper_model = whisper.load_model("base")
    logger.info("Whisper model loaded (cached)")
    return _whisper_model


def transcribe_whisper(samples: np.ndarray, sample_rate: int, language: str) -> RecognitionResult:
    if samples.size == 0:
        return RecognitionResult("", 0.0, language, 0.0)

    with debug_timer("Whisper recognition"):
        model = _load_whisper_model()
        wav_bytes = _samples_to_wav_bytes(samples, sample_rate)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(wav_bytes)
            tmp.flush()
            result = model.transcribe(tmp.name, language=language if language != "auto" else None)

    text = normalize_transcript(str(result.get("text", "")))
    duration = len(samples) / max(sample_rate, 1)
    confidence = 0.85 if text else 0.0
    detected = str(result.get("language", language))
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Whisper confidence=%.2f language=%s duration=%.2fs", confidence, detected, duration)
    return RecognitionResult(text=text, confidence=confidence, language=detected, duration=duration)


def transcribe_speech_recognition(samples: np.ndarray, sample_rate: int, language: str) -> RecognitionResult:
    import speech_recognition as sr

    if samples.size == 0:
        return RecognitionResult("", 0.0, language, 0.0)

    recognizer = sr.Recognizer()
    wav_bytes = _samples_to_wav_bytes(samples, sample_rate)
    with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
        audio = recognizer.record(source)

    with debug_timer("SpeechRecognition fallback"):
        try:
            text = recognizer.recognize_sphinx(audio, language=language)
            confidence = 0.55
        except Exception as exc:
            logger.warning("SpeechRecognition fallback failed: %s", exc)
            return RecognitionResult("", 0.0, language, len(samples) / sample_rate)

    return RecognitionResult(
        text=normalize_transcript(text),
        confidence=confidence,
        language=language,
        duration=len(samples) / sample_rate,
    )


def transcribe(samples: np.ndarray, sample_rate: int, language: str = "en") -> RecognitionResult:
    try:
        return transcribe_whisper(samples, sample_rate, language)
    except Exception as exc:
        logger.warning("Whisper unavailable, falling back: %s", exc)
        return transcribe_speech_recognition(samples, sample_rate, language)
