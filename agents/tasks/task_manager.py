"""Autonomous task orchestration: queue, run, cancel, pause, memory."""

from __future__ import annotations

import logging
import threading
import time

from agents.tasks.progress import (
    ProgressEvent,
    ProgressEventType,
    ProgressTracker,
    emit_progress,
)
from agents.tasks.scheduler import estimate_remaining_seconds, ready_subtasks, run_parallel_batch
from agents.tasks.task import ExecutionSummary, Task, TaskResult, TaskStatus, SubTask
from agents.tasks.task_executor import execute_subtask
from agents.tasks.task_planner import plan_from_goal
from agents.tasks.task_queue import TaskQueue

logger = logging.getLogger(__name__)

BACKOFF_BASE_SECONDS = 1.5
MAX_BACKOFF_SECONDS = 30.0

_global_tracker = ProgressTracker()
_global_queue = TaskQueue()
_cancel_flags: dict[str, bool] = {}
_lock = threading.RLock()


def get_progress_tracker() -> ProgressTracker:
    """Return shared progress state for desktop/voice status queries."""
    return _global_tracker


def get_idle_status() -> str:
    """Short status line for voice ('What are you doing?')."""
    return _global_tracker.status_line()


def _set_cancel(task_id: str, value: bool) -> None:
    with _lock:
        _cancel_flags[task_id] = value


def _is_cancelled(task_id: str) -> bool:
    with _lock:
        return _cancel_flags.get(task_id, False)


def _save_task_memory(summary: ExecutionSummary) -> bool:
    """Persist a durable summary of a completed autonomous goal."""
    if not summary.success or not summary.report.strip():
        return False
    text = f"Autonomous task completed — {summary.title}: {summary.report[:500]}"
    try:
        from memory.store import save_memory

        return save_memory(text)
    except Exception as exc:
        logger.debug("Autonomous memory save skipped: %s", exc)
        return False


def _retry_delay(retry_count: int) -> float:
    return min(MAX_BACKOFF_SECONDS, BACKOFF_BASE_SECONDS ** (retry_count + 1))


def _run_subtask_with_retry(task: Task, subtask: SubTask) -> TaskResult:
    while True:
        if _is_cancelled(task.id):
            subtask.status = TaskStatus.CANCELLED
            return TaskResult(
                task_id=task.id,
                subtask_id=subtask.id,
                success=False,
                summary="Cancelled",
                retryable=False,
            )
        result = execute_subtask(task, subtask)
        if result.success:
            return result
        if subtask.permanent_failure or not result.retryable:
            return result
        if subtask.retry_count >= subtask.max_retries:
            return result
        subtask.retry_count += 1
        _global_tracker.retries += 1
        delay = _retry_delay(subtask.retry_count)
        emit_progress(
            ProgressEvent(
                ProgressEventType.TASK_RETRY,
                task_id=task.id,
                subtask_id=subtask.id,
                message=f"Retry {subtask.retry_count} after {delay:.1f}s",
            )
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Retry subtask %s (%s/%s) in %.1fs",
                subtask.title,
                subtask.retry_count,
                subtask.max_retries,
                delay,
            )
        time.sleep(delay)
        subtask.status = TaskStatus.PENDING
        subtask.error = ""


def run_task(task: Task, *, save_memory: bool = True) -> ExecutionSummary:
    """Execute all subtasks respecting dependencies."""
    start = time.perf_counter()
    _set_cancel(task.id, False)
    task.status = TaskStatus.RUNNING
    task.touch()

    _global_tracker.idle = False
    _global_tracker.task_id = task.id
    _global_tracker.total = len(task.subtasks)
    _global_tracker.completed = 0
    _global_tracker.errors = []
    _global_tracker.retries = 0
    _global_tracker.paused = False

    emit_progress(
        ProgressEvent(
            ProgressEventType.TASK_STARTED,
            task_id=task.id,
            message=task.title,
        )
    )
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Task created: %s (%s subtasks)", task.title, len(task.subtasks))
        deps = [f"{s.title}<-{s.depends_on}" for s in task.subtasks if s.depends_on]
        if deps:
            logger.debug("Dependencies: %s", "; ".join(deps))
    try:
        from plugins.events import Event, emit

        emit(Event.TASK_STARTED, {"task_id": task.id, "title": task.title})
    except Exception:
        pass

    results: list[TaskResult] = []
    failed = False

    while True:
        if _is_cancelled(task.id):
            task.status = TaskStatus.CANCELLED
            break
        if _global_queue.should_wait():
            _global_tracker.paused = True
            time.sleep(0.2)
            continue
        _global_tracker.paused = False

        batch = ready_subtasks(task)
        if not batch:
            pending = [s for s in task.subtasks if s.status not in {
                TaskStatus.COMPLETED,
                TaskStatus.CANCELLED,
                TaskStatus.FAILED,
            }]
            if not pending:
                break
            if any(s.status == TaskStatus.FAILED for s in task.subtasks):
                failed = True
                break
            time.sleep(0.05)
            continue

        for subtask in batch:
            _global_tracker.current_title = subtask.title
            emit_progress(
                ProgressEvent(
                    ProgressEventType.SUBTASK_STARTED,
                    task_id=task.id,
                    subtask_id=subtask.id,
                    message=subtask.title,
                )
            )

        parallel_safe = all(len(s.depends_on) == 0 for s in batch) and len(batch) > 1
        if parallel_safe:
            outcomes = run_parallel_batch(
                task,
                batch,
                cancel_check=lambda: _is_cancelled(task.id),
                pause_check=lambda: _global_queue.paused,
            )
            for subtask, outcome in outcomes:
                if isinstance(outcome, TaskResult):
                    result = outcome
                elif isinstance(outcome, Exception):
                    result = TaskResult(
                        task_id=task.id,
                        subtask_id=subtask.id,
                        success=False,
                        summary=subtask.title,
                        detail=str(outcome),
                    )
                else:
                    result = outcome
                results.append(result)
                _finalize_subtask(task, subtask, result)
                if not result.success:
                    failed = True
        else:
            for subtask in batch:
                result = _run_subtask_with_retry(task, subtask)
                results.append(result)
                _finalize_subtask(task, subtask, result)
                if not result.success:
                    failed = True
                    break
        if failed:
            break

    elapsed = time.perf_counter() - start
    report = _build_report(task, results)
    success = not failed and all(
        s.status == TaskStatus.COMPLETED for s in task.subtasks
    )
    task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
    task.touch()

    summary = ExecutionSummary(
        task_id=task.id,
        title=task.title,
        success=success,
        report=report,
        subtask_results=results,
        elapsed_seconds=elapsed,
    )
    if save_memory and success:
        summary.memory_saved = _save_task_memory(summary)

    _global_tracker.idle = True
    _global_tracker.current_title = ""
    _global_tracker.completed = sum(
        1 for s in task.subtasks if s.status == TaskStatus.COMPLETED
    )

    event_type = (
        ProgressEventType.TASK_COMPLETED
        if success
        else ProgressEventType.TASK_FAILED
    )
    emit_progress(
        ProgressEvent(
            event_type,
            task_id=task.id,
            message=report[:200],
        )
    )
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Task %s: success=%s elapsed=%.1fs summary=%s chars",
            task.id,
            success,
            elapsed,
            len(report),
        )

    try:
        from plugins.events import Event, emit

        emit(
            Event.TASK_FINISHED,
            {"task_id": task.id, "success": success, "elapsed_seconds": elapsed},
        )
    except Exception:
        pass

    emit_progress(
        ProgressEvent(ProgressEventType.QUEUE_IDLE, task_id="", message="Idle")
    )
    return summary


def _finalize_subtask(task: Task, subtask: SubTask, result: TaskResult) -> None:
    if result.success:
        _global_tracker.completed += 1
        emit_progress(
            ProgressEvent(
                ProgressEventType.SUBTASK_COMPLETED,
                task_id=task.id,
                subtask_id=subtask.id,
                message=result.summary,
            )
        )
    else:
        _global_tracker.errors = _global_tracker.errors or []
        _global_tracker.errors.append(result.detail or result.summary)
        emit_progress(
            ProgressEvent(
                ProgressEventType.SUBTASK_FAILED,
                task_id=task.id,
                subtask_id=subtask.id,
                message=result.detail or result.summary,
            )
        )


def _build_report(task: Task, results: list[TaskResult]) -> str:
    lines = [f"# {task.title}", "", task.description, ""]
    for step in task.subtasks:
        status = step.status.value
        lines.append(f"## {step.title} ({status})")
        if step.result_summary:
            lines.append(step.result_summary)
        elif step.error:
            lines.append(f"Error: {step.error}")
        lines.append("")
    for result in results:
        if result.detail and result.success:
            lines.append(result.detail[:1500])
            lines.append("")
    return "\n".join(lines).strip()


def run_autonomous_goal(query: str, *, save_memory: bool = True) -> ExecutionSummary | None:
    """Plan and run an autonomous goal, or return None if bypassed."""
    task = plan_from_goal(query)
    if task is None:
        return None
    return run_task(task, save_memory=save_memory)


def cancel_task(task_id: str) -> bool:
    """Cancel a running or queued task."""
    _set_cancel(task_id, True)
    return _global_queue.remove_task(task_id)


def cancel_all_tasks() -> int:
    """Cancel the queue and signal running work to stop."""
    return _global_queue.cancel_all()


def pause_queue() -> None:
    _global_queue.pause()


def resume_queue() -> None:
    _global_queue.resume()


def enqueue_task(task: Task) -> None:
    _global_queue.enqueue(task)
