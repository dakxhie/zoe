"""Telemetry tests (create only)."""

from __future__ import annotations

from deployment.config import load_config, reset_config_for_tests
from deployment.telemetry import record_telemetry, summarize_telemetry


def test_record_telemetry_local():
    reset_config_for_tests()
    load_config()
    record_telemetry("test_event", {"ok": True})
    summary = summarize_telemetry()
    assert "by_type" in summary
