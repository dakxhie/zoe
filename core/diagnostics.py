"""Informational startup diagnostics for Zoe AI.

Surfaces index and model availability without raising. Individual probes are
isolated so one unavailable subsystem (e.g. missing Chroma) cannot blank the
whole startup banner. Exactly five lines are returned — Memory, Notes, PDF,
Code, Model — a contract relied on by CLI/desktop banners and tests.
"""

from __future__ import annotations

import logging

from core.chroma import ChromaError, collection_count, get_chroma_path
from core.config import load_settings
from core.index_status import (
    COLLECTION_CODE,
    COLLECTION_MEMORY,
    COLLECTION_NOTES,
    COLLECTION_PDF,
)

logger = logging.getLogger(__name__)


def _format_index_status(name: str, count: int) -> str:
    """Format an index status line with collection counts."""
    return f"✓ {name} ({count})"


def _memory_count() -> int:
    """Return the number of stored memories, or zero when unavailable."""
    try:
        get_chroma_path()
        return collection_count(COLLECTION_MEMORY)
    except (ChromaError, OSError):
        return 0


def _check_model_available() -> str:
    """Verify the configured model name is present without loading weights."""
    model_name = load_settings().get("MODEL_NAME", "").strip()
    if model_name:
        return f"✓ Model available ({model_name})"
    return "✓ Model unavailable (MODEL_NAME missing)"


def run_startup_diagnostics() -> list[str]:
    """Return startup status lines. Never raises."""
    lines: list[str] = []

    try:
        lines.append(_format_index_status("Memory", _memory_count()))
    except Exception as exc:
        logger.debug("Startup Memory probe failed: %s", exc)
        lines.append("✓ Memory (0)")

    try:
        lines.append(_format_index_status("Notes", collection_count(COLLECTION_NOTES)))
    except Exception as exc:
        logger.debug("Startup Notes probe failed: %s", exc)
        lines.append("✓ Notes (0)")

    try:
        lines.append(_format_index_status("PDF", collection_count(COLLECTION_PDF)))
    except Exception as exc:
        logger.debug("Startup PDF probe failed: %s", exc)
        lines.append("✓ PDF (0)")

    try:
        lines.append(_format_index_status("Code", collection_count(COLLECTION_CODE)))
    except Exception as exc:
        logger.debug("Startup Code probe failed: %s", exc)
        lines.append("✓ Code (0)")

    try:
        lines.append(_check_model_available())
    except Exception as exc:
        logger.debug("Startup Model probe failed: %s", exc)
        lines.append("✓ Model unavailable")

    return lines


def print_startup_diagnostics() -> None:
    """Print startup diagnostics to stdout. Never raises."""
    for line in run_startup_diagnostics():
        print(line)
