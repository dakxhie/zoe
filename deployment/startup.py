"""Startup sequence with optional timing (DEBUG)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from core.config import ROOT
from deployment.config import get_config, load_config
from deployment.telemetry import record_telemetry

logger = logging.getLogger(__name__)


@dataclass
class StartupReport:
    steps: list[tuple[str, float]] = field(default_factory=list)
    success: bool = True
    messages: list[str] = field(default_factory=list)
    diagnostic_lines: list[str] = field(default_factory=list)

    @property
    def total_seconds(self) -> float:
        return sum(duration for _, duration in self.steps)


def _step(name: str, fn, report: StartupReport) -> None:
    start = time.perf_counter()
    try:
        fn()
        elapsed = time.perf_counter() - start
        report.steps.append((name, elapsed))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Startup step %s completed in %.3fs", name, elapsed)
    except Exception as exc:
        elapsed = time.perf_counter() - start
        report.steps.append((name, elapsed))
        report.success = False
        report.messages.append(f"{name}: {exc}")
        logger.warning("Startup step %s failed: %s", name, exc)


def _verify_folders() -> None:
    expected = (
        ROOT / "data",
        ROOT / "data" / "history",
        ROOT / "cache",
        ROOT / "storage",
    )
    for path in expected:
        path.mkdir(parents=True, exist_ok=True)


def run_startup_sequence(
    *,
    load_model: bool = False,
    initialize_voice: bool = False,
    initialize_desktop: bool = False,
    cli_overrides: dict | None = None,
) -> StartupReport:
    """Run the production startup pipeline (additive; safe when called multiple times)."""
    report = StartupReport()
    total_start = time.perf_counter()

    load_config(cli_overrides=cli_overrides)
    cfg = get_config()

    from core.logging_config import configure_logging

    configure_logging(level=cfg.logging_level())

    _step("load_config", lambda: None, report)

    if cfg.raw.get("startup", {}).get("verify_folders", True):
        _step("verify_folders", _verify_folders, report)

    _step(
        "initialize_plugins",
        lambda: __import__("plugins.manager", fromlist=["initialize_plugins"]).initialize_plugins(),
        report,
    )

    _step("initialize_memory", lambda: __import__("core.chroma", fromlist=["get_chroma_path"]).get_chroma_path(), report)

    if load_model:
        def _load():
            from brain.generation import load_model

            load_model()

        _step("initialize_models", _load, report)
    else:
        _step("initialize_models", lambda: None, report)

    if cfg.raw.get("startup", {}).get("initialize_agents", True):
        _step("initialize_agents", lambda: None, report)

    if initialize_voice:
        _step(
            "initialize_voice",
            lambda: __import__("voice.deps", fromlist=["voice_capture_available"]).voice_capture_available(),
            report,
        )

    if initialize_desktop:
        _step("initialize_desktop", lambda: Path(ROOT / "desktop").exists(), report)

    def _capture_diagnostics() -> None:
        lines = __import__(
            "core.diagnostics", fromlist=["run_startup_diagnostics"]
        ).run_startup_diagnostics()
        report.diagnostic_lines = list(lines)

    _step("startup_diagnostics", _capture_diagnostics, report)

    total = time.perf_counter() - total_start
    record_telemetry(
        "startup",
        {"success": report.success, "total_seconds": total, "steps": len(report.steps)},
    )
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Startup total %.3fs (%s steps)", total, len(report.steps))

    return report
