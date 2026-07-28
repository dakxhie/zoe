"""Pytest coverage for startup diagnostics."""

from __future__ import annotations

from unittest.mock import patch

from core.diagnostics import run_startup_diagnostics


def test_startup_diagnostics_reports_all_subsystems() -> None:
    """Report memory, indexes, and model availability."""
    with patch("core.diagnostics.get_chroma_path"), patch(
        "core.diagnostics.collection_count",
        side_effect=[2, 0, 5, 1],
    ), patch(
        "core.diagnostics.load_settings",
        return_value={"MODEL_NAME": "Qwen/Qwen2.5-3B-Instruct"},
    ):
        lines = run_startup_diagnostics()

    assert any("Memory database ready" in line for line in lines)
    assert any("Notes index ready" in line for line in lines)
    assert any("PDF index empty" in line for line in lines)
    assert any("Code index ready" in line for line in lines)
    assert any("Model available" in line for line in lines)
    assert len(lines) == 5
