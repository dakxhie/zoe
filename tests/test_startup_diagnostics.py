"""Pytest coverage for startup diagnostics."""

from __future__ import annotations

from unittest.mock import patch

from core.diagnostics import run_startup_diagnostics


def test_startup_diagnostics_reports_collection_counts() -> None:
    """Report memory and index counts."""
    with patch("core.diagnostics._memory_count", return_value=15), patch(
        "core.diagnostics.collection_count",
        side_effect=[42, 381, 1270],
    ), patch(
        "core.diagnostics.load_settings",
        return_value={"MODEL_NAME": "Qwen/Qwen2.5-3B-Instruct"},
    ):
        lines = run_startup_diagnostics()

    assert "Memory (15)" in lines[0]
    assert "Notes (42)" in lines[1]
    assert "PDF (381)" in lines[2]
    assert "Code (1270)" in lines[3]
    assert "Model available" in lines[4]
    assert len(lines) == 5


def test_startup_diagnostics_shows_zero_for_empty_indexes() -> None:
    """Show zero counts for empty collections."""
    with patch("core.diagnostics._memory_count", return_value=0), patch(
        "core.diagnostics.collection_count",
        return_value=0,
    ), patch(
        "core.diagnostics.load_settings",
        return_value={"MODEL_NAME": "Qwen/Qwen2.5-3B-Instruct"},
    ):
        lines = run_startup_diagnostics()

    assert lines[0] == "✓ Memory (0)"
    assert lines[1] == "✓ Notes (0)"
    assert lines[2] == "✓ PDF (0)"
    assert lines[3] == "✓ Code (0)"
