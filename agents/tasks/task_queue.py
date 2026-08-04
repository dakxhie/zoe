"""FIFO task queue with priority, dependencies, and lifecycle control."""

from __future__ import annotations

import logging
import threading
from collections import deque

from agents.tasks.progress import ProgressEvent, ProgressEventType, emit_progress
from agents.tasks.task import SubTask, Task, TaskStatus

logger = logging.getLogger(__name__)


class TaskQueue:
    """Thread-safe queue of autonomous tasks."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tasks: deque[Task] = deque()
        self._paused = False
        self._cancel_all = False

    @property
    def paused(self) -> bool:
        with self._lock:
            return self._paused

    def enqueue(self, task: Task) -> None:
        with self._lock:
            self._tasks.append(task)
            self._sort_by_priority()

    def _sort_by_priority(self) -> None:
        items = list(self._tasks)
        items.sort(key=lambda item: (-item.priority, item.created_at))
        self._tasks = deque(items)

    def peek(self) -> Task | None:
        with self._lock:
            return self._tasks[0] if self._tasks else None

    def dequeue(self) -> Task | None:
        with self._lock:
            if not self._tasks:
                return None
            return self._tasks.popleft()

    def remove_task(self, task_id: str) -> bool:
        with self._lock:
            for index, task in enumerate(self._tasks):
                if task.id == task_id:
                    task.status = TaskStatus.CANCELLED
                    task.touch()
                    del self._tasks[index]
                    emit_progress(
                        ProgressEvent(
                            ProgressEventType.TASK_CANCELLED,
                            task_id=task_id,
                            message="Task removed from queue",
                        )
                    )
                    return True
            return False

    def cancel_all(self) -> int:
        with self._lock:
            self._cancel_all = True
            count = len(self._tasks)
            for task in self._tasks:
                task.status = TaskStatus.CANCELLED
                task.touch()
                emit_progress(
                    ProgressEvent(
                        ProgressEventType.TASK_CANCELLED,
                        task_id=task.id,
                        message="Queue cancelled",
                    )
                )
            self._tasks.clear()
            return count

    def pause(self) -> None:
        with self._lock:
            self._paused = True
            emit_progress(
                ProgressEvent(
                    ProgressEventType.TASK_PAUSED,
                    task_id="",
                    message="Task queue paused",
                )
            )

    def resume(self) -> None:
        with self._lock:
            self._paused = False
            self._cancel_all = False
            emit_progress(
                ProgressEvent(
                    ProgressEventType.TASK_RESUMED,
                    task_id="",
                    message="Task queue resumed",
                )
            )

    def should_wait(self) -> bool:
        with self._lock:
            return self._paused or self._cancel_all

    def retry_queue(self) -> list[SubTask]:
        """Return subtasks marked for retry (managed by executor)."""
        return []

    def __len__(self) -> int:
        with self._lock:
            return len(self._tasks)

    def pending_subtasks(self, task: Task) -> list[SubTask]:
        """Subtasks ready to run (dependencies satisfied)."""
        completed = {
            step.id
            for step in task.subtasks
            if step.status == TaskStatus.COMPLETED
        }
        ready: list[SubTask] = []
        for step in task.subtasks:
            if step.status not in {TaskStatus.PENDING, TaskStatus.WAITING}:
                continue
            if all(dep in completed for dep in step.depends_on):
                ready.append(step)
        return ready

    def mark_dependency_wait(self, task: Task) -> None:
        for step in task.subtasks:
            if step.status != TaskStatus.PENDING:
                continue
            completed = {
                s.id for s in task.subtasks if s.status == TaskStatus.COMPLETED
            }
            if step.depends_on and not all(d in completed for d in step.depends_on):
                step.status = TaskStatus.WAITING
