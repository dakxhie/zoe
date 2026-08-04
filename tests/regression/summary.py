"""Persist regression summaries to disk."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from tests.regression.report import RegressionReport
from tests.regression.utils import REPORTS_DIR


def write_latest_report(report: RegressionReport, *, mode: str) -> Path:
    """Write tests/reports/latest.txt and return the path."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    target = REPORTS_DIR / "latest.txt"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    header = [
        "Zoe AI regression summary",
        f"Mode: {mode}",
        f"Generated: {timestamp}",
        "",
    ]
    body = report.render_plain_lines()
    target.write_text("\n".join(header + body) + "\n", encoding="utf-8")
    return target
