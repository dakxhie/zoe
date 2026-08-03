"""Wake / push-to-talk helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WakeConfig:
    """Manual wake configuration (future wake-word ready)."""

    mode: str = "push_to_talk"


def is_manual_wake_enabled(config: WakeConfig) -> bool:
    """Return True when voice should activate only on user action."""
    return config.mode == "push_to_talk"
