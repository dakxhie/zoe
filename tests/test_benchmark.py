"""Benchmark framework tests (create only)."""

from __future__ import annotations

from deployment.benchmark import run_benchmark_suite


def test_benchmark_suite_structure():
    report = run_benchmark_suite(include_model=False)
    names = {r.name for r in report.results}
    assert "startup" in names
    assert "tool_execution" in names
