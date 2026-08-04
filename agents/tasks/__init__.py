"""Autonomous task engine for Zoe AI."""

from agents.tasks.progress import (
    ProgressEvent,
    ProgressEventType,
    ProgressTracker,
    emit_progress,
    subscribe_progress,
    unsubscribe_progress,
)
from agents.tasks.task import (
    ExecutionSummary,
    SubTask,
    Task,
    TaskExecution,
    TaskProgress,
    TaskResult,
    TaskStatus,
)
from agents.tasks.task_manager import (
    cancel_all_tasks,
    cancel_task,
    enqueue_task,
    get_idle_status,
    get_progress_tracker,
    pause_queue,
    resume_queue,
    run_autonomous_goal,
    run_task,
)
from agents.tasks.task_planner import plan_from_goal, should_autonomous_execute

__all__ = [
    "ExecutionSummary",
    "ProgressEvent",
    "ProgressEventType",
    "ProgressTracker",
    "SubTask",
    "Task",
    "TaskExecution",
    "TaskProgress",
    "TaskResult",
    "TaskStatus",
    "cancel_all_tasks",
    "cancel_task",
    "emit_progress",
    "enqueue_task",
    "get_idle_status",
    "get_progress_tracker",
    "pause_queue",
    "plan_from_goal",
    "resume_queue",
    "run_autonomous_goal",
    "run_task",
    "should_autonomous_execute",
    "subscribe_progress",
    "unsubscribe_progress",
]
