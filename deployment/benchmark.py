"""Benchmark utilities for Zoe production readiness."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    name: str
    seconds: float
    success: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    results: list[BenchmarkResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": [
                {
                    "name": r.name,
                    "seconds": r.seconds,
                    "success": r.success,
                    "details": r.details,
                }
                for r in self.results
            ],
            "total_seconds": sum(r.seconds for r in self.results),
        }


def _measure(name: str, fn: Callable[[], None]) -> BenchmarkResult:
    start = time.perf_counter()
    success = True
    details: dict[str, Any] = {}
    try:
        fn()
    except Exception as exc:
        success = False
        details["error"] = str(exc)
    elapsed = time.perf_counter() - start
    return BenchmarkResult(name=name, seconds=elapsed, success=success, details=details)


def run_benchmark_suite(*, include_model: bool = False) -> BenchmarkReport:
    """Run structured benchmarks (safe without GPU model load by default)."""
    report = BenchmarkReport()

    report.results.append(
        _measure(
            "startup",
            lambda: __import__(
                "deployment.startup", fromlist=["run_startup_sequence"]
            ).run_startup_sequence(),
        )
    )

    def _plugin_load():
        from plugins.manager import initialize_plugins

        initialize_plugins(force=True)

    report.results.append(_measure("plugin_load", _plugin_load))

    def _embedding():
        from rag.embedder import embed_texts

        embed_texts(["benchmark probe"])

    report.results.append(_measure("embedding_latency", _embedding))

    def _memory_retrieval():
        from memory.retriever import search_memories

        search_memories("benchmark", top_k=1)

    report.results.append(_measure("memory_retrieval", _memory_retrieval))

    def _tool_execution():
        from tools.calculator import calculate

        calculate("1+1")

    report.results.append(_measure("tool_execution", _tool_execution))

    if include_model:
        def _first_token():
            from brain.generation import generate_text, load_model

            tok, model = load_model()
            generate_text(tok, model, [{"role": "user", "content": "Hi"}], max_new_tokens=8)

        report.results.append(_measure("first_token", _first_token))
        report.results.append(_measure("response_latency", _first_token))

    def _autonomous_stub():
        from agents.tasks.task_planner import should_autonomous_execute

        should_autonomous_execute("analyze this large codebase thoroughly")

    report.results.append(_measure("autonomous_task_planning", _autonomous_stub))

    return report
