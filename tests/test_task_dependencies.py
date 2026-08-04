"""Unit tests for task dependencies and retry (not executed in sprint)."""

from __future__ import annotations

from unittest.mock import patch

from agents.tasks.task import SubTask, Task, TaskStatus
from agents.tasks.task_executor import execute_subtask
from agents.tasks.task_manager import _retry_delay, _run_subtask_with_retry


def test_retry_delay_increases() -> None:
    assert _retry_delay(0) < _retry_delay(2)


@patch("agents.tasks.task_executor._dispatch_action", side_effect=[RuntimeError("temporary"), ("ok", "")])
def test_retry_on_transient_failure(mock_dispatch) -> None:
    task = Task.create("T", "d")
    step = SubTask.create("S", "d", "index_project", max_retries=2)
    task.subtasks = [step]
    with patch("agents.tasks.task_manager.time.sleep"):
        result = _run_subtask_with_retry(task, step)
    assert result.success is True


def test_permanent_failure_not_retried() -> None:
    task = Task.create("T", "d")
    step = SubTask.create("S", "d", "unknown_action_xyz")
    with patch("agents.tasks.task_manager.time.sleep"):
        result = _run_subtask_with_retry(task, step)
    assert result.success is False
