"""Shutdown sequence tests (create only)."""

from __future__ import annotations

from deployment.shutdown import run_shutdown_sequence


def test_shutdown_sequence_runs():
    steps = run_shutdown_sequence()
    assert any(name == "plugins" for name, _ in steps)
