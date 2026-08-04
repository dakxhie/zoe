"""Resource monitor tests (create only)."""

from __future__ import annotations

from deployment.resource_monitor import capture_resource_snapshot


def test_capture_resource_snapshot():
    snap = capture_resource_snapshot()
    assert snap.plugin_count >= 0
    assert snap.memory_count >= 0
