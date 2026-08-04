"""Background workers for Zoe Desktop (non-blocking UI)."""

from __future__ import annotations

import logging
import time
import traceback
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThread, QThreadPool, Signal, Slot

logger = logging.getLogger(__name__)


@dataclass
class WorkerResult:
    """Generic worker result container."""

    ok: bool
    data: Any = None
    error: str = ""


class WorkerSignals(QObject):
    """Signals shared by runnable workers."""

    started = Signal(str)
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(str)


class FunctionWorker(QRunnable):
    """Run a callable on the global thread pool."""

    def __init__(self, name: str, fn, *args, **kwargs) -> None:
        super().__init__()
        self.name = name
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        self.signals.started.emit(self.name)
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(WorkerResult(ok=True, data=result))
        except Exception as exc:
            logger.exception("Worker %s failed", self.name)
            self.signals.failed.emit(f"{exc}\n{traceback.format_exc(limit=2)}")


class ChatWorker(QThread):
    """Generate a chat response using the existing brain pipeline."""

    completed = Signal(str)
    failed = Signal(str)
    started = Signal()

    def __init__(self, prompt: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.prompt = prompt
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        self.started.emit()
        start = time.perf_counter()
        try:
            from brain.pipeline import generate_response

            if self._cancelled:
                return
            reply = generate_response(self.prompt)
            if self._cancelled:
                return
            elapsed = time.perf_counter() - start
            logger.info("Desktop chat generation finished in %.2fs", elapsed)
            self.completed.emit(reply)
        except Exception as exc:
            self.failed.emit(str(exc))


class VisionWorker(QThread):
    """Analyze an image via the existing vision + chat pipeline."""

    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, image_path: str, prompt: str = "", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.image_path = image_path
        self.prompt = prompt

    def run(self) -> None:
        try:
            from brain.pipeline import generate_image_response

            reply = generate_image_response(self.image_path, self.prompt)
            self.completed.emit(reply)
        except Exception as exc:
            self.failed.emit(str(exc))


class StartupWorker(QThread):
    """Load startup diagnostics without blocking the splash screen."""

    line_ready = Signal(str)
    finished_ok = Signal(list)

    def run(self) -> None:
        lines: list[str] = []
        try:
            self.line_ready.emit("Loading deployment config...")
            from deployment.config import load_config
            from deployment.startup import run_startup_sequence

            load_config()
            report = run_startup_sequence(initialize_desktop=True)
            self.line_ready.emit("Loading settings...")
            from core.config import load_settings

            load_settings()
            lines = list(report.diagnostic_lines)
            if not lines:
                from core.diagnostics import run_startup_diagnostics

                lines = run_startup_diagnostics()
            for line in lines:
                self.line_ready.emit(line)
        except Exception as exc:
            lines.append(f"Startup warning: {exc}")
        self.finished_ok.emit(lines)


def submit_pool(name: str, fn, *args, pool: QThreadPool | None = None, **kwargs) -> FunctionWorker:
    """Submit a function worker and return the worker instance."""
    worker = FunctionWorker(name, fn, *args, **kwargs)
    target_pool = pool or QThreadPool.globalInstance()
    target_pool.start(worker)
    return worker


def run_index_notes() -> int:
    from rag.retriever import build_index

    return build_index()


def run_index_pdfs() -> int:
    from pdf.indexer import build_pdf_index

    return build_pdf_index()


def run_index_code(project_path: str) -> tuple[int, int]:
    from codebase.indexer import build_code_index

    return build_code_index(project_path)


def list_desktop_plugin_summary() -> list[dict[str, str | bool]]:
    """Expose loaded/enabled plugins for desktop settings (no UI redesign)."""
    from plugins.manager import list_plugin_status

    return [
        {
            "id": row.plugin_id,
            "name": row.name,
            "enabled": row.enabled,
            "health": row.health,
        }
        for row in list_plugin_status()
    ]


def run_doctor_report():
    from core.doctor import run_doctor

    return run_doctor()


def run_project_analysis_text(query: str) -> tuple[bool, str]:
    from agents.analyzer import run_project_analysis

    return run_project_analysis(query)


def get_autonomous_task_status() -> str:
    """Status line for UI/voice: current task, progress, or idle."""
    from agents.tasks.task_manager import get_progress_tracker

    tracker = get_progress_tracker()
    progress = tracker.snapshot()
    if progress.idle:
        return "Idle"
    return f"{tracker.current_title or 'Working'} ({progress.completed}/{progress.total})"


def connect_autonomous_progress(callback) -> None:
    """Subscribe desktop WorkerSignals.progress to autonomous task events."""
    from agents.tasks.progress import ProgressEvent, subscribe_progress

    def _relay(event: ProgressEvent) -> None:
        callback(event.message)

    subscribe_progress(_relay)
