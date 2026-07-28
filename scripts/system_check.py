"""Verify all Zoe AI subsystems are operational."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.analyzer import run_project_analysis
from agents.planner import build_plan, is_project_analysis_query
from memory.history import add_message, clear_history, get_history
from memory.retriever import search_memories
from memory.store import save_memory
from pdf.retriever import search_documents
from codebase.retriever import search_code
from rag.retriever import search
from tools.calculator import calculate
from tools.datetime_tool import get_datetime_response
from tools.executor import execute_tool
from tools.filesystem import list_files, read_file
from tools.router import route_query


def _check(name: str, passed: bool) -> bool:
    """Print PASS or FAIL for one subsystem."""
    status = "PASS" if passed else "FAIL"
    print(f"{status}  {name}")
    return passed


def main() -> None:
    """Run subsystem checks and print a final readiness summary."""
    results: list[bool] = []

    try:
        saved = save_memory("System check memory probe.")
        memory_results = search_memories("system check", top_k=1)
        results.append(_check("Memory", saved and isinstance(memory_results, list)))
    except Exception:
        results.append(_check("Memory", False))

    try:
        note_results = search("notes", top_k=1)
        results.append(_check("Notes RAG", isinstance(note_results, list)))
    except Exception:
        results.append(_check("Notes RAG", False))

    try:
        pdf_results = search_documents("introduction", top_k=1)
        results.append(_check("PDF retrieval", isinstance(pdf_results, list)))
    except Exception:
        results.append(_check("PDF retrieval", False))

    try:
        code_results = search_code("generate_response", top_k=1)
        results.append(_check("Code retrieval", isinstance(code_results, list)))
    except Exception:
        results.append(_check("Code retrieval", False))

    try:
        clear_history()
        add_message("user", "system check")
        history = get_history(max_messages=1)
        results.append(
            _check(
                "Conversation history",
                len(history) == 1 and history[0]["content"] == "system check",
            )
        )
    except Exception:
        results.append(_check("Conversation history", False))

    try:
        plan = build_plan()
        query = "Analyze this Python project and tell me how to improve it."
        results.append(
            _check(
                "Planner",
                is_project_analysis_query(query) and len(plan) == 5,
            )
        )
    except Exception:
        results.append(_check("Planner", False))

    try:
        results.append(
            _check(
                "Tool router",
                route_query("Hello!") == "chat"
                and route_query("What is my favorite color?") == "memory",
            )
        )
    except Exception:
        results.append(_check("Tool router", False))

    try:
        handled, result = execute_tool("2+2")
        results.append(_check("Tool executor", handled and result == "4"))
    except Exception:
        results.append(_check("Tool executor", False))

    try:
        files = list_files(".")
        readme = read_file("README.md", max_lines=3)
        results.append(
            _check(
                "Filesystem",
                bool(files.strip()) and bool(readme.strip()),
            )
        )
    except Exception:
        results.append(_check("Filesystem", False))

    try:
        results.append(_check("Calculator", calculate("3+4") == "7"))
    except Exception:
        results.append(_check("Calculator", False))

    try:
        results.append(
            _check("Datetime", get_datetime_response("Current time") is not None)
        )
    except Exception:
        results.append(_check("Datetime", False))

    try:
        is_analysis, context = run_project_analysis(
            "Analyze this Python project and tell me how to improve it."
        )
        results.append(
            _check(
                "Project analyzer",
                is_analysis and "Project Analysis" in context,
            )
        )
    except Exception:
        results.append(_check("Project analyzer", False))

    print("\nSystem Ready")

    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
