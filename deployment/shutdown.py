"""Graceful shutdown sequence."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


def run_shutdown_sequence() -> list[tuple[str, float]]:
    """Shutdown subsystems in safe order. Never raises."""
    steps: list[tuple[str, float]] = []

    def _run(name: str, fn) -> None:
        start = time.perf_counter()
        try:
            fn()
        except Exception as exc:
            logger.warning("Shutdown step %s failed: %s", name, exc)
        steps.append((name, time.perf_counter() - start))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Shutdown step %s in %.3fs", name, steps[-1][1])

    _run("task_queues", _shutdown_tasks)
    _run("voice", _shutdown_voice)
    _run("desktop", lambda: None)
    _run("models", _shutdown_models)
    _run("plugins", _shutdown_plugins)
    _run("event_system", lambda: None)
    _run("vector_db", lambda: None)

    try:
        from plugins.events import Event, emit

        emit(Event.SHUTDOWN, {})
    except Exception:
        pass

    try:
        from deployment.telemetry import record_telemetry

        record_telemetry("shutdown", {"steps": len(steps)})
    except Exception:
        pass

    return steps


def _shutdown_tasks() -> None:
    try:
        from agents.tasks.task_manager import cancel_all_tasks

        cancel_all_tasks()
    except Exception:
        pass


def _shutdown_voice() -> None:
    pass


def _shutdown_models() -> None:
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _shutdown_plugins() -> None:
    from plugins.manager import shutdown_plugins

    shutdown_plugins()
