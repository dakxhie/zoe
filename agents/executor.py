"""Execution steps for Zoe AI agent workflows."""

from __future__ import annotations

import logging

from codebase.retriever import search_code
from tools.filesystem import FilesystemError, read_file

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
            blocks.append(
                f"[{result['path']} | {result['language']}]\n{result['content']}"
            )

    if not blocks:
        return "No indexed code results found. Run `python cli/main.py code .` first."

    return "\n\n".join(blocks)


def _format_file_reads() -> str:
    """Read key project files and format their contents."""
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

    return (
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
