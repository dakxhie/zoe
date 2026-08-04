"""Rich deployment diagnostics report."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from deployment.environment import detect_environment
from deployment.health import overall_health, run_health_checks
from deployment.resource_monitor import capture_resource_snapshot

logger = logging.getLogger(__name__)


@dataclass
class DeploymentDiagnostics:
    environment: dict[str, str] = field(default_factory=dict)
    health_summary: str = ""
    health_checks: list[tuple[str, str, list[str]]] = field(default_factory=list)
    resources: dict[str, object] = field(default_factory=dict)
    lines: list[str] = field(default_factory=list)


def run_deployment_diagnostics(*, rich: bool | None = None) -> DeploymentDiagnostics:
    diag = DeploymentDiagnostics()
    diag.environment = detect_environment()

    try:
        from deployment.config import get_config

        cfg = get_config()
        use_rich = cfg.rich_diagnostics() if rich is None else rich
    except Exception:
        use_rich = True

    checks = run_health_checks()
    diag.health_summary = overall_health(checks).value
    for check in checks:
        diag.health_checks.append((check.name, check.status.value, check.details))

    snap = capture_resource_snapshot()
    diag.resources = {
        "plugin_count": snap.plugin_count,
        "memory_count": snap.memory_count,
        "history_bytes": snap.history_bytes,
        "vector_db_bytes": snap.vector_db_bytes,
        "model_name": snap.model_name,
    }

    diag.lines.append(f"Profile: {diag.environment.get('profile', 'unknown')}")
    diag.lines.append(f"Health: {diag.health_summary}")
    if use_rich:
        for name, status, details in diag.health_checks:
            diag.lines.append(f"  [{status}] {name}: {'; '.join(details[:3])}")
        diag.lines.append(
            f"Resources: plugins={snap.plugin_count} memories={snap.memory_count}"
        )

    try:
        from core.diagnostics import run_startup_diagnostics

        diag.lines.extend(run_startup_diagnostics())
    except Exception as exc:
        diag.lines.append(f"Startup diagnostics unavailable: {exc}")

    return diag
