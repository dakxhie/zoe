"""Voice utility helpers."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def debug_timer(label: str):
    """Log elapsed time when DEBUG logging is enabled."""
    start = time.perf_counter()
    try:
        yield
    finally:
        if logger.isEnabledFor(logging.DEBUG):
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug("%s took %.1f ms", label, elapsed)


def normalize_transcript(text: str) -> str:
    """Normalize recognized speech text."""
    return " ".join(text.strip().split())
