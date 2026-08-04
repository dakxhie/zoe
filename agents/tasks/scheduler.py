"""Dependency-aware scheduling and parallel batch selection."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.tasks.task import SubTask, Task, TaskStatus
from agents.tasks.task_executor import execute_subtask

logger = logging.getLogger(__name__)

MAX_PARALLEL_SUBTASKS = 3


def ready_subtasks(task: Task) -> list[SubTask]:
    """Return subtasks whose dependencies are completed."""
    completed_ids = {
        step.id for step in task.subtasks if step.status == TaskStatus.COMPLETED
    }
    ready: list[SubTask] = []
    for step in task.subtasks:
        if step.status not in {TaskStatus.PENDING, TaskStatus.WAITING}:
            continue
        if all(dep in completed_ids for dep in step.depends_on):
            if step.status == TaskStatus.WAITING:
                step.status = TaskStatus.PENDING
            ready.append(step)
    return ready


def next_sequential_subtask(task: Task) -> SubTask | None:
    """Return the next subtask in dependency order (single-threaded fallback)."""
    batch = ready_subtasks(task)
    if not batch:
        return None
    return batch[0]


def run_parallel_batch(
    task: Task,
    subtasks: list[SubTask],
    *,
    cancel_check,
    pause_check,
) -> list[tuple[SubTask, object]]:
    """Execute independent ready subtasks in parallel when safe."""
    if len(subtasks) <= 1:
        results: list[tuple[SubTask, object]] = []
        for step in subtasks:
            if cancel_check():
                break
            while pause_check():
                if cancel_check():
                    break
            results.append((step, execute_subtask(task, step)))
        return results

    independent = [s for s in subtasks if not s.depends_on]
    if len(independent) < 2:
        step = subtasks[0]
        return [(step, execute_subtask(task, step))]

    parallel = independent[:MAX_PARALLEL_SUBTASKS]
    outcomes: list[tuple[SubTask, object]] = []

    with ThreadPoolExecutor(max_workers=len(parallel)) as pool:
        futures = {
            pool.submit(execute_subtask, task, step): step for step in parallel
        }
        for future in as_completed(futures):
            step = futures[future]
            if cancel_check():
                future.cancel()
                continue
            try:
                outcomes.append((step, future.result()))
            except Exception as exc:
                logger.warning("Parallel subtask %s failed: %s", step.id, exc)
                outcomes.append((step, exc))
    return outcomes


def estimate_remaining_seconds(task: Task) -> float:
    """Rough ETA from pending subtask estimates."""
    total = 0.0
    for step in task.subtasks:
        if step.status not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}:
            total += step.estimated_seconds
    return total
