"""Console report formatting for Zoe regression runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from tests.regression.utils import TerminalColors


class ScenarioStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class ScenarioOutcome:
    """Result of one regression scenario."""

    key: str
    label: str
    status: ScenarioStatus
    detail: str = ""
    duration_s: float = 0.0


@dataclass
class RegressionReport:
    """Aggregated regression results."""

    outcomes: list[ScenarioOutcome] = field(default_factory=list)
    total_duration_s: float = 0.0

    def add(self, outcome: ScenarioOutcome) -> None:
        self.outcomes.append(outcome)

    @property
    def passed(self) -> int:
        return sum(1 for item in self.outcomes if item.status == ScenarioStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for item in self.outcomes if item.status == ScenarioStatus.FAIL)

    @property
    def warnings(self) -> int:
        return sum(1 for item in self.outcomes if item.status == ScenarioStatus.WARN)

    def render_console(self, colors: TerminalColors | None = None) -> str:
        palette = colors or TerminalColors()
        width = 37
        lines: list[str] = []
        lines.append("=" * width)
        lines.append("ZOE REGRESSION REPORT")
        lines.append("=" * width)
        lines.append("")

        for outcome in self.outcomes:
            status_text = self._format_status(outcome.status, palette)
            dots = "." * max(1, 22 - len(outcome.label))
            lines.append(f"{outcome.label} {dots} {status_text}")

        lines.append("")
        lines.append("=" * width)
        lines.append("")
        lines.append("TOTAL")
        lines.append("")
        lines.append(f"Passed: {self.passed}")
        lines.append(f"Failed: {self.failed}")
        lines.append(f"Warnings: {self.warnings}")
        lines.append(f"Time: {self.total_duration_s:.1f} seconds")
        lines.append("")
        lines.append("=" * width)
        return "\n".join(lines)

    def render_plain_lines(self) -> list[str]:
        """Plain-text lines for tests/reports/latest.txt (no ANSI)."""
        rows: list[str] = []
        for outcome in self.outcomes:
            rows.append(f"{outcome.status.value} {outcome.label}")
            if outcome.detail:
                rows.append(f"  {outcome.detail}")
        rows.append("")
        rows.append(f"Passed: {self.passed}")
        rows.append(f"Failed: {self.failed}")
        rows.append(f"Warnings: {self.warnings}")
        rows.append(f"Time: {self.total_duration_s:.1f} seconds")
        return rows

    @staticmethod
    def _format_status(status: ScenarioStatus, palette: TerminalColors) -> str:
        if status == ScenarioStatus.PASS:
            return palette.pass_label("PASS")
        if status == ScenarioStatus.WARN:
            return palette.warn_label("WARN")
        if status == ScenarioStatus.FAIL:
            return palette.fail_label("FAIL")
        return palette.info_label("SKIP")
