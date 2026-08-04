"""Regression test runner for Zoe AI."""

from __future__ import annotations

import time
from typing import Sequence

from core.logging_config import configure_logging

from tests.regression.report import RegressionReport, ScenarioOutcome, ScenarioStatus
from tests.regression.scenarios import FULL_SCENARIOS, QUICK_SCENARIOS
from tests.regression.summary import write_latest_report
from tests.regression.utils import (
    TerminalColors,
    delete_regression_memories,
    ensure_project_root,
    regression_memory_cleanup,
)


class RegressionRunner:
    """Runs regression scenarios sequentially without stopping on failure."""

    def __init__(self, *, full: bool = False) -> None:
        ensure_project_root()
        configure_logging()
        self.full = full
        self.colors = TerminalColors()

    def run(self) -> RegressionReport:
        scenarios: Sequence = FULL_SCENARIOS if self.full else QUICK_SCENARIOS
        report = RegressionReport()
        start = time.perf_counter()

        with regression_memory_cleanup():
            for scenario_fn in scenarios:
                outcome = scenario_fn()
                report.add(outcome)

        report.total_duration_s = time.perf_counter() - start
        delete_regression_memories()
        return report

    def print_report(self, report: RegressionReport) -> None:
        print(report.render_console(self.colors))

    def write_summary(self, report: RegressionReport) -> None:
        mode = "full" if self.full else "quick"
        path = write_latest_report(report, mode=mode)
        print(self.colors.info_label(f"Summary written to {path}"))


def run_regression(*, full: bool = False) -> int:
    """Run regression tests and return a process exit code."""
    runner = RegressionRunner(full=full)
    report = runner.run()
    runner.print_report(report)
    runner.write_summary(report)
    return 1 if report.failed > 0 else 0
