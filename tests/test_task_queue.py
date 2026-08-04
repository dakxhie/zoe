"""Unit tests for task queue (not executed in sprint)."""

from __future__ import annotations

from agents.tasks.task import Task, TaskStatus
from agents.tasks.task_planner import plan_project_analysis_task
from agents.tasks.task_queue import TaskQueue


def test_fifo_with_priority() -> None:
    queue = TaskQueue()
    low = Task.create("Low", "l", priority=1)
    high = Task.create("High", "h", priority=10)
    queue.enqueue(low)
    queue.enqueue(high)
    assert queue.peek() is high


def test_pause_and_resume() -> None:
    queue = TaskQueue()
    queue.pause()
    assert queue.paused is True
    queue.resume()
    assert queue.paused is False


def test_ready_subtasks_respects_dependencies() -> None:
    queue = TaskQueue()
    task = plan_project_analysis_task("Analyze")
    ready = queue.pending_subtasks(task)
    assert len(ready) == 1
    assert ready[0].title == "Index project"
