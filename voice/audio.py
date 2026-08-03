"""Audio device discovery and capture helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000


@dataclass(frozen=True)
class AudioDevice:
    """One audio input or output device."""

    index: int
    name: str
    kind: str


def list_input_devices() -> list[AudioDevice]:
    """Return available microphone devices."""
    devices: list[AudioDevice] = []
    try:
        import sounddevice as sd

        for index, info in enumerate(sd.query_devices()):
            if info["max_input_channels"] > 0:
                devices.append(AudioDevice(index=index, name=str(info["name"]), kind="input"))
    except Exception as exc:
        logger.warning("Could not enumerate input devices: %s", exc)
    return devices


def list_output_devices() -> list[AudioDevice]:
    """Return available speaker devices."""
    devices: list[AudioDevice] = []
    try:
        import sounddevice as sd

        for index, info in enumerate(sd.query_devices()):
            if info["max_output_channels"] > 0:
                devices.append(AudioDevice(index=index, name=str(info["name"]), kind="output"))
    except Exception as exc:
        logger.warning("Could not enumerate output devices: %s", exc)
    return devices


def reduce_noise(samples: np.ndarray) -> np.ndarray:
    """Apply a simple noise gate."""
    if samples.size == 0:
        return samples
    peak = float(np.max(np.abs(samples)))
    if peak < 1e-6:
        return samples
    normalized = samples / peak
    gate = np.where(np.abs(normalized) < 0.01, 0.0, normalized)
    return gate.astype(np.float32)


def resolve_input_device_index(device_name: str) -> int | None:
    """Resolve configured device name to sounddevice index."""
    if not device_name:
        return None
    for device in list_input_devices():
        if device.name == device_name or str(device.index) == device_name:
            return device.index
    return None
