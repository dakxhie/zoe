"""Execute individual autonomous subtasks using existing Zoe backends."""

from __future__ import annotations

import logging
import time

from agents.tasks.task import SubTask, Task, TaskResult, TaskStatus

logger = logging.getLogger(__name__)

PERMANENT_FAILURE_MARKERS: tuple[str, ...] = (
    "invalid path",
    "permission denied",
    "not found:",
    "configuration missing",
)


def _is_permanent_error(message: str) -> bool:
    lowered = message.lower()
    return any(marker in lowered for marker in PERMANENT_FAILURE_MARKERS)


def execute_subtask(task: Task, subtask: SubTask) -> TaskResult:
    """Run one subtask action and return structured result."""
    start = time.perf_counter()
    subtask.status = TaskStatus.RUNNING
    query = task.goal_query or task.description

    try:
        summary, detail = _dispatch_action(subtask.action, query)
        subtask.status = TaskStatus.COMPLETED
        subtask.result_summary = summary
        elapsed = time.perf_counter() - start
        logger.debug(
            "Subtask %s completed in %.1fs: %s",
            subtask.title,
            elapsed,
            summary[:80],
        )
        return TaskResult(
            task_id=task.id,
            subtask_id=subtask.id,
            success=True,
            summary=summary,
            detail=detail,
        )
    except Exception as exc:
        message = str(exc)
        subtask.error = message
        permanent = _is_permanent_error(message)
        subtask.permanent_failure = permanent
        subtask.status = TaskStatus.FAILED
        return TaskResult(
            task_id=task.id,
            subtask_id=subtask.id,
            success=False,
            summary=f"{subtask.title} failed",
            detail=message,
            retryable=not permanent,
        )


def _dispatch_action(action: str, query: str) -> tuple[str, str]:
    """Map internal action ids to existing subsystems."""
    if action == "index_project":
        from codebase.indexer import build_code_index
        from core.config import ROOT

        files, chunks = build_code_index(ROOT)
        return (
            f"Indexed {files} file(s), {chunks} chunk(s).",
            f"code_index files={files} chunks={chunks}",
        )

    if action == "detect_framework":
        from agents.project_report import build_project_report, format_project_report

        report = format_project_report(build_project_report())
        return ("Framework and language detected.", report[:2000])

    if action == "analyze_architecture":
        from agents.executor import execute_project_analysis

        context = execute_project_analysis(query)
        return ("Architecture context gathered.", context[:4000])

    if action == "review_code_quality":
        from codebase.retriever import search_code

        hits = search_code("complexity hotspot refactor test", top_k=5)
        if not hits:
            return ("No code index hits; suggest running code indexing.", "")
        lines = [f"{h.get('path')}: {h.get('content', '')[:200]}" for h in hits]
        return ("Code quality scan complete.", "\n".join(lines))

    if action == "summarize_report":
        from agents.analyzer import run_project_analysis

        is_analysis, context = run_project_analysis(query)
        if not is_analysis:
            return ("Summary prepared from gathered steps.", context[:3000])
        return ("Project analysis summary ready.", context[:5000])

    if action == "research_web":
        from web.retriever import retrieve_web_context

        text = retrieve_web_context(query, max_pages=2)
        return ("Web research complete.", text[:3000])

    if action == "memory_snapshot":
        from memory.retriever import search_memories

        hits = search_memories(query, top_k=5)
        combined = "; ".join(h["content"][:120] for h in hits)
        return ("Memory snapshot collected.", combined)

    raise ValueError(f"Unknown autonomous action: {action}")
