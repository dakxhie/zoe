"""Microphone capture with silence detection."""

from __future__ import annotations

import logging
import threading

import numpy as np

from voice.audio import SAMPLE_RATE, reduce_noise, resolve_input_device_index

logger = logging.getLogger(__name__)


class CaptureResult:
    """Recorded audio samples."""

    __slots__ = ("samples", "sample_rate", "duration")

    def __init__(self, samples: np.ndarray, sample_rate: int, duration: float) -> None:
        self.samples = samples
        self.sample_rate = sample_rate
        self.duration = duration


class AudioListener:
    """Capture audio until silence or manual stop."""

    def __init__(
        self,
        *,
        silence_seconds: float = 2.5,
        noise_threshold: float = 0.015,
        input_device: str = "",
    ) -> None:
        self.silence_seconds = silence_seconds
        self.noise_threshold = noise_threshold
        self.input_device = input_device
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def record_until_silence(self, max_seconds: float = 30.0) -> CaptureResult:
        """Record from the microphone until silence is detected."""
        from voice.deps import voice_capture_available

        if not voice_capture_available():
            raise RuntimeError(
                "Microphone capture unavailable. Install optional voice dependencies: "
                "pip install -r requirements-voice.txt"
            )

        import sounddevice as sd

        device_index = resolve_input_device_index(self.input_device)
        frames: list[np.ndarray] = []
        silent_blocks = 0
        block_duration = 0.1
        block_size = int(SAMPLE_RATE * block_duration)
        max_blocks = int(max_seconds / block_duration)
        self._stop_event.clear()

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=block_size,
            device=device_index,
        ) as stream:
            for _ in range(max_blocks):
                if self._stop_event.is_set():
                    break
                block, _overflowed = stream.read(block_size)
                chunk = np.asarray(block, dtype=np.float32).reshape(-1)
                chunk = reduce_noise(chunk)
                frames.append(chunk)
                if float(np.max(np.abs(chunk))) < self.noise_threshold:
                    silent_blocks += 1
                else:
                    silent_blocks = 0
                if len(frames) > int(0.5 / block_duration) and silent_blocks * block_duration >= self.silence_seconds:
                    break

        if not frames:
            return CaptureResult(np.array([], dtype=np.float32), SAMPLE_RATE, 0.0)

        samples = np.concatenate(frames)
        duration = len(samples) / SAMPLE_RATE
        return CaptureResult(samples, SAMPLE_RATE, duration)
