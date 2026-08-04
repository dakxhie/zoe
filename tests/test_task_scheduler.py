"""Unit tests for task scheduler (not executed in sprint)."""

from __future__ import annotations

from agents.tasks.scheduler import estimate_remaining_seconds, ready_subtasks
from agents.tasks.task import TaskStatus
from agents.tasks.task_planner import plan_project_analysis_task


def test_ready_after_first_completes() -> None:
    task = plan_project_analysis_task("Analyze")
    task.subtasks[0].status = TaskStatus.COMPLETED
    ready = ready_subtasks(task)
    titles = {step.title for step in ready}
    assert "Detect framework" in titles


def test_estimate_remaining() -> None:
    task = plan_project_analysis_task("Analyze")
    assert estimate_remaining_seconds(task) > 0
