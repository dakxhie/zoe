"""Startup sequence tests (create only)."""

from __future__ import annotations

from deployment.config import load_config, reset_config_for_tests
from deployment.startup import run_startup_sequence


def test_startup_sequence_success():
    reset_config_for_tests()
    load_config()
    report = run_startup_sequence()
    assert report.success
    assert any(name == "load_config" for name, _ in report.steps)
