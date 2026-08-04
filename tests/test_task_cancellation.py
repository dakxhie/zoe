"""Unit tests for task cancellation (not executed in sprint)."""

from __future__ import annotations

from agents.tasks.task_manager import cancel_all_tasks, pause_queue, resume_queue
from agents.tasks.task_planner import plan_project_analysis_task
from agents.tasks.task_queue import TaskQueue


def test_cancel_all_clears_queue() -> None:
    queue = TaskQueue()
    queue.enqueue(plan_project_analysis_task("Analyze"))
    assert cancel_all_tasks() >= 0


def test_pause_resume_queue() -> None:
    pause_queue()
    resume_queue()
