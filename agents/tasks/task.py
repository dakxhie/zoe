"""Autonomous task models for Zoe AI."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


@dataclass
class SubTask:
    """One step inside an autonomous task."""

    id: str
    title: str
    description: str
    action: str
    depends_on: tuple[str, ...] = ()
    estimated_seconds: float = 30.0
    max_retries: int = 2
    retry_count: int = 0
    status: TaskStatus = TaskStatus.PENDING
    result_summary: str = ""
    error: str = ""
    permanent_failure: bool = False

    @staticmethod
    def create(
        title: str,
        description: str,
        action: str,
        *,
        depends_on: tuple[str, ...] = (),
        estimated_seconds: float = 30.0,
        max_retries: int = 2,
    ) -> SubTask:
        return SubTask(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            action=action,
            depends_on=depends_on,
            estimated_seconds=estimated_seconds,
            max_retries=max_retries,
        )


@dataclass
class Task:
    """A multi-step autonomous goal."""

    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    subtasks: list[SubTask] = field(default_factory=list)
    dependencies: tuple[str, ...] = ()
    estimated_duration_seconds: float = 0.0
    max_retries: int = 1
    retry_count: int = 0
    created_at: str = field(default_factory=lambda: _iso(_utc_now()))
    updated_at: str = field(default_factory=lambda: _iso(_utc_now()))
    goal_query: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = _iso(_utc_now())

    @staticmethod
    def create(
        title: str,
        description: str,
        *,
        goal_query: str = "",
        priority: int = 0,
        subtasks: list[SubTask] | None = None,
    ) -> Task:
        steps = subtasks or []
        estimate = sum(step.estimated_seconds for step in steps)
        return Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            priority=priority,
            subtasks=steps,
            estimated_duration_seconds=estimate,
            goal_query=goal_query or description,
        )


@dataclass
class TaskResult:
    """Outcome of one subtask or whole task."""

    task_id: str
    subtask_id: str | None
    success: bool
    summary: str
    detail: str = ""
    retryable: bool = True


@dataclass
class TaskProgress:
    """Snapshot of queue progress."""

    current_subtask_id: str | None
    current_subtask_title: str
    completed: int
    remaining: int
    total: int
    elapsed_seconds: float
    estimated_remaining_seconds: float
    errors: list[str] = field(default_factory=list)
    retries: int = 0
    queue_paused: bool = False
    idle: bool = True


@dataclass
class TaskExecution:
    """Runtime record for one subtask execution."""

    subtask_id: str
    started_at: str
    finished_at: str = ""
    status: TaskStatus = TaskStatus.RUNNING
    result: TaskResult | None = None


@dataclass
class ExecutionSummary:
    """Final report for a completed autonomous goal."""

    task_id: str
    title: str
    success: bool
    report: str
    subtask_results: list[TaskResult] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    memory_saved: bool = False
