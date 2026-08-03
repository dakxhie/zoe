"""Execution engine for Zoe AI agent workflows."""

from __future__ import annotations

import logging
import time

from agents.fusion import fuse_tool_outputs
from agents.recovery import retry_once, run_with_recovery, vision_fallback_caption_only, vision_fallback_ocr_only
from agents.state import AgentState, ExecutionResult, PlanStep, ToolOutput
from core.index_status import EMPTY_INDEX_MESSAGES, TOOL_COLLECTIONS
from core.chroma import collection_count
from tools.router import extract_image_path

logger = logging.getLogger(__name__)

IMPORTANT_FILES: tuple[str, ...] = (
    "README.md",
    "docs/ARCHITECTURE.md",
    "requirements.txt",
    "brain/model.py",
    "cli/main.py",
)

CODE_SEARCH_TERMS: tuple[str, ...] = (
    "architecture",
    "generate_response",
    "build_index",
    "execute_tool",
)

MAX_FILE_LINES = 80
MAX_CODE_RESULTS = 3


def _format_code_results(query: str) -> str:
    """Search indexed code and format the results."""
    from codebase.retriever import search_code

    searches = [query, *CODE_SEARCH_TERMS]
    seen: set[str] = set()
    blocks: list[str] = []

    for term in searches:
        try:
            results = search_code(term, top_k=MAX_CODE_RESULTS)
        except Exception as exc:
            logger.warning("Project analysis code search failed for '%s': %s", term, exc)
            continue

        for result in results:
            key = f"{result['path']}:{result['content'][:80]}"
            if key in seen:
                continue
            seen.add(key)
            blocks.append(f"[{result['path']} | {result['language']}]\n{result['content']}")

    if not blocks:
        return "No indexed code results found. Run `python cli/main.py code .` first."

    return "\n\n".join(blocks)


def _format_file_reads() -> str:
    """Read key project files and format their contents."""
    from tools.filesystem import FilesystemError, read_file

    blocks: list[str] = []

    for path in IMPORTANT_FILES:
        try:
            content = read_file(path, max_lines=MAX_FILE_LINES)
        except FilesystemError as exc:
            blocks.append(f"--- {path} ---\n{exc}")
            continue

        blocks.append(f"--- {path} ---\n{content}")

    return "\n\n".join(blocks)


def execute_project_analysis(query: str) -> str:
    """Execute the project analysis plan and return gathered context."""
    code_section = _format_code_results(query)
    files_section = _format_file_reads()
    gathered = (
        "========================\n"
        "Project Analysis\n"
        "========================\n\n"
        "Code Search Results:\n"
        f"{code_section}\n\n"
        "Important Files:\n"
        f"{files_section}\n\n"
        "Instructions:\n"
        "Use the project analysis context above to summarize the architecture "
        "and recommend concrete improvements. Do not ask the user for more files or code."
    )
    logger.info("Executor finished gathering %s characters of analysis context", len(gathered))
    return gathered


def _confidence_for_content(content: str, *, base: float = 0.75) -> float:
    if not content.strip():
        return 0.0
    if len(content) < 40:
        return min(base, 0.45)
    return min(0.95, base + min(len(content) / 5000, 0.2))


def _run_tool(tool: str, query: str, detail: str, state: AgentState) -> ToolOutput:
    """Execute one tool step and return structured output."""
    start = time.perf_counter()
    content = ""
    source = tool
    success = True
    error = ""

    try:
        if tool == "memory":
            from brain.context import _join_content, _retrieve_memories

            results = _retrieve_memories(query if not detail.startswith("chapter") else detail, top_k=3)
            content = _join_content(results)
            source = "zoe_memory"
        elif tool == "notes":
            from brain.context import _join_content, _retrieve_notes

            results = _retrieve_notes(query, top_k=3)
            content = _join_content(results)
            source = "zoe_notes"
        elif tool == "pdf":
            from brain.context import _join_content, _retrieve_documents

            search_query = detail if detail.startswith("chapter") else query
            results = _retrieve_documents(search_query, top_k=5)
            content = _join_content(results)
            source = "zoe_documents"
        elif tool == "code":
            from brain.context import _join_content, _retrieve_code

            results = _retrieve_code(query, top_k=5)
            content = _join_content(results)
            source = "zoe_code"
        elif tool == "conversation":
            from brain.context import _retrieve_conversation

            content = _retrieve_conversation(query)
            source = "conversation_history"
        elif tool == "web":
            from brain.context import _prepare_web_context

            def _web_fetch() -> str:
                web_context, _stats = _prepare_web_context(query)
                return web_context

            fetched, warning = retry_once("web retrieval", _web_fetch)
            if warning:
                state.execution = state.execution or ExecutionResult(success=True)
                if state.execution.warnings is not None:
                    state.execution.warnings.append(warning)
            content = fetched or ""
            source = "web"
            success = bool(content.strip())
        elif tool == "vision":
            image_path = extract_image_path(query)
            if not image_path:
                raise ValueError("No image path found")
            from brain.context import _retrieve_vision, build_vision_context

            vision_result = _retrieve_vision(image_path, prompt=query)
            vision_result = vision_fallback_caption_only(vision_result)
            vision_result = vision_fallback_ocr_only(vision_result)
            content = build_vision_context(vision_result)
            source = image_path
            success = bool(content.strip())
        elif tool == "project_analysis":
            from agents.project_report import build_project_report, format_project_report

            content = execute_project_analysis(query)
            structured = format_project_report(build_project_report())
            content = f"{structured}\n\n{content}"
            source = "project_analyzer"
        elif tool in {"llm", "chat"}:
            content = ""
            source = tool
        else:
            raise ValueError(f"Unsupported tool: {tool}")
    except Exception as exc:
        success = False
        error = str(exc)
        logger.warning("Tool execution failed for %s: %s", tool, exc)

    elapsed_ms = (time.perf_counter() - start) * 1000
    confidence = _confidence_for_content(content) if success else 0.0

    return ToolOutput(
        tool=tool,
        content=content,
        confidence=confidence,
        execution_time_ms=elapsed_ms,
        source=source,
        success=success,
        error=error,
    )


def _empty_index_message(tool: str) -> str | None:
    collection_name = TOOL_COLLECTIONS.get(tool)
    if collection_name is None:
        return None
    if collection_count(collection_name) == 0:
        return EMPTY_INDEX_MESSAGES.get(tool)
    return None


def execute_agent_plan(state: AgentState) -> ExecutionResult:
    """Execute the agent plan, recover from partial failures, and fuse context."""
    warnings: list[str] = []
    errors: list[str] = []
    outputs: list[ToolOutput] = []

    retrieval_start = time.perf_counter()
    executed_tools: set[str] = set()

    for step in state.plan:
        if step.tool in {"llm", "chat"}:
            state.completed_steps.append(step)
            continue

        tool_key = f"{step.tool}:{step.detail}"
        if tool_key in executed_tools and step.tool not in {"pdf"}:
            continue
        executed_tools.add(tool_key)

        output, warning = run_with_recovery(
            f"{step.tool} step",
            lambda: _run_tool(step.tool, state.goal, step.detail, state),
            warning_message=f"{step.tool} retrieval unavailable",
        )
        if warning:
            warnings.append(warning)

        if output is None:
            state.failed_steps.append(step)
            errors.append(f"{step.tool} failed")
            fallback_message = _empty_index_message(step.tool)
            if fallback_message:
                warnings.append(fallback_message)
            continue

        if not output.success or not output.content.strip():
            state.failed_steps.append(step)
            if output.error:
                errors.append(output.error)
            if step.tool == "code":
                fallback_output, fallback_warning = run_with_recovery(
                    "project analyzer fallback",
                    lambda: _run_tool("project_analysis", state.goal, step.detail, state),
                )
                if fallback_warning:
                    warnings.append(fallback_warning)
                if fallback_output and fallback_output.content.strip():
                    outputs.append(fallback_output)
                    state.completed_steps.append(step)
                    continue
        else:
            state.completed_steps.append(step)

        outputs.append(output)

    if state.intent and "memory" not in {item.tool for item in outputs}:
        memory_output, warning = run_with_recovery(
            "memory enrichment",
            lambda: _run_tool("memory", state.goal, state.goal, state),
        )
        if warning:
            warnings.append(warning)
        if memory_output and memory_output.content.strip():
            outputs.insert(0, memory_output)

    conversation_output, warning = run_with_recovery(
        "conversation enrichment",
        lambda: _run_tool("conversation", state.goal, state.goal, state),
    )
    if warning:
        warnings.append(warning)
    if conversation_output and conversation_output.content.strip():
        outputs.insert(0, conversation_output)

    state.tool_outputs = outputs
    state.timings.retrieval_ms = (time.perf_counter() - retrieval_start) * 1000
    state.timings.tool_ms = sum(item.execution_time_ms for item in outputs)
    state.fused_context = fuse_tool_outputs(outputs)

    result = ExecutionResult(
        success=bool(outputs) or not errors,
        steps=list(state.plan),
        outputs=outputs,
        warnings=warnings,
        errors=errors,
    )
    state.execution = result
    logger.debug(
        "Execution finished: success=%s outputs=%s warnings=%s errors=%s",
        result.success,
        len(outputs),
        len(warnings),
        len(errors),
    )
    return result
