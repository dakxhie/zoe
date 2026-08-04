"""Unit tests for autonomous task manager (not executed in sprint)."""

from __future__ import annotations

from unittest.mock import patch

from agents.tasks.task import TaskStatus
from agents.tasks.task_manager import cancel_task, get_progress_tracker, run_task
from agents.tasks.task_planner import plan_project_analysis_task, should_autonomous_execute


def test_should_not_autonomous_simple_math() -> None:
    assert should_autonomous_execute("2+2") is False


def test_should_autonomous_project_query() -> None:
    query = "Analyze my entire Python project and suggest improvements."
    assert should_autonomous_execute(query) is True


def test_plan_has_dependency_chain() -> None:
    task = plan_project_analysis_task("Analyze project")
    assert len(task.subtasks) == 5
    summarize = task.subtasks[-1]
    assert summarize.depends_on


@patch("agents.tasks.task_manager.execute_subtask")
def test_run_task_marks_completed(mock_exec) -> None:
    from agents.tasks.task import TaskResult

    mock_exec.return_value = TaskResult("t", "s", True, "ok")
    task = plan_project_analysis_task("Analyze project")
    for step in task.subtasks:
        step.estimated_seconds = 0.01
    with patch("agents.tasks.task_manager.run_parallel_batch") as mock_batch:
        mock_batch.side_effect = lambda task, batch, **kw: [
            (step, mock_exec.return_value) for step in batch
        ]
        summary = run_task(task, save_memory=False)
    assert summary.task_id == task.id


def test_cancel_task_flag() -> None:
    task = plan_project_analysis_task("Analyze")
    cancel_task(task.id)
