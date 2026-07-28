"""Informational startup diagnostics for Zoe AI."""

from __future__ import annotations

from core.chroma import ChromaError, collection_count, get_chroma_path
from core.config import load_settings
from core.index_status import (
    COLLECTION_CODE,
    COLLECTION_MEMORY,
    COLLECTION_NOTES,
    COLLECTION_PDF,
)


def _format_index_status(name: str, count: int) -> str:
    """Format an index status line for ready or empty collections."""
    if count > 0:
        return f"✓ {name} index ready ({count} item(s))"
    return f"✓ {name} index empty"


def _check_memory_database() -> str:
    """Verify the memory database path and collection are accessible."""
    try:
        get_chroma_path()
        collection_count(COLLECTION_MEMORY)
        return "✓ Memory database ready"
    except (ChromaError, OSError):
        return "✓ Memory database unavailable"


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
        lines.append(_check_memory_database())
    except Exception:
        lines.append("✓ Memory database unavailable")

    try:
        notes_count = collection_count(COLLECTION_NOTES)
        lines.append(_format_index_status("Notes", notes_count))
    except Exception:
        lines.append("✓ Notes index empty")

    try:
        pdf_count = collection_count(COLLECTION_PDF)
        lines.append(_format_index_status("PDF", pdf_count))
    except Exception:
        lines.append("✓ PDF index empty")

    try:
        code_count = collection_count(COLLECTION_CODE)
        lines.append(_format_index_status("Code", code_count))
    except Exception:
        lines.append("✓ Code index empty")

    try:
        lines.append(_check_model_available())
    except Exception:
        lines.append("✓ Model unavailable")

    return lines


def print_startup_diagnostics() -> None:
    """Print startup diagnostics to stdout. Never raises."""
    for line in run_startup_diagnostics():
        print(line)
