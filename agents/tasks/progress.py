"""Progress events for autonomous tasks (desktop/voice can subscribe later)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)

ProgressListener = Callable[["ProgressEvent"], None]

_listeners: list[ProgressListener] = []


class ProgressEventType(str, Enum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRY = "task_retry"
    TASK_CANCELLED = "task_cancelled"
    TASK_PAUSED = "task_paused"
    TASK_RESUMED = "task_resumed"
    SUBTASK_STARTED = "subtask_started"
    SUBTASK_COMPLETED = "subtask_completed"
    SUBTASK_FAILED = "subtask_failed"
    QUEUE_IDLE = "queue_idle"


@dataclass(frozen=True)
class ProgressEvent:
    """Event emitted during autonomous execution."""

    type: ProgressEventType
    task_id: str
    message: str
    subtask_id: str | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(
                self,
                "timestamp",
                datetime.now(timezone.utc).isoformat(),
            )


def subscribe_progress(listener: ProgressListener) -> None:
    """Register a callback for progress events (e.g. desktop UI adapter)."""
    if listener not in _listeners:
        _listeners.append(listener)


def unsubscribe_progress(listener: ProgressListener) -> None:
    """Remove a progress listener."""
    if listener in _listeners:
        _listeners.remove(listener)


def emit_progress(event: ProgressEvent) -> None:
    """Broadcast a progress event to subscribers."""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Progress [%s] task=%s subtask=%s: %s",
            event.type.value,
            event.task_id,
            event.subtask_id,
            event.message,
        )
    for listener in list(_listeners):
        try:
            listener(event)
        except Exception as exc:
            logger.warning("Progress listener failed: %s", exc)


@dataclass
class ProgressTracker:
    """Tracks current autonomous run for status queries."""

    task_id: str = ""
    current_title: str = ""
    completed: int = 0
    total: int = 0
    elapsed_seconds: float = 0.0
    errors: list[str] | None = None
    retries: int = 0
    paused: bool = False
    idle: bool = True

    def snapshot(self, *, estimated_remaining: float = 0.0) -> "TaskProgress":
        from agents.tasks.task import TaskProgress

        remaining = max(0, self.total - self.completed)
        return TaskProgress(
            current_subtask_id=None,
            current_subtask_title=self.current_title,
            completed=self.completed,
            remaining=remaining,
            total=self.total,
            elapsed_seconds=self.elapsed_seconds,
            estimated_remaining_seconds=estimated_remaining,
            errors=list(self.errors or []),
            retries=self.retries,
            queue_paused=self.paused,
            idle=self.idle,
        )

    def status_line(self) -> str:
        """Human-readable status for voice ('What are you doing?')."""
        if self.idle:
            return "Idle — no autonomous task is running."
        if self.paused:
            return f"Paused: {self.current_title or 'autonomous task'}."
        if self.current_title:
            return f"Currently working on: {self.current_title}."
        return "Running an autonomous task."
