"""Health monitor tests (create only — not executed)."""

from __future__ import annotations

from deployment.health import HealthStatus, run_health_checks


def test_run_health_checks_returns_results():
    results = run_health_checks()
    assert len(results) >= 5
    names = {r.name for r in results}
    assert "configuration" in names
    assert "plugins" in names


def test_health_status_enum():
    assert HealthStatus.HEALTHY.value == "healthy"
