"""End-to-end smoke test for Zoe AI subsystems."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.logging_config import configure_logging
from code.indexer import build_code_index
from code.retriever import search_code
from memory.retriever import search_memories
from memory.store import save_memory
from pdf.indexer import build_pdf_index
from pdf.retriever import search_documents
from rag.retriever import build_index, search

configure_logging()


def _print_step(name: str, detail: str) -> None:
    """Print one test step result."""
    print(f"[PASS] {name}: {detail}")


def _assert_true(condition: bool, message: str) -> None:
    """Raise when a test assertion fails."""
    if not condition:
        raise AssertionError(message)


def main() -> None:
    """Run automated integration checks without manual interaction."""
    print("Running Zoe full system test...\n")

    notes_count = build_index()
    _print_step("Notes indexing", f"{notes_count} new note(s)")
    note_results = search("favorite programming language", top_k=3)
    _assert_true(isinstance(note_results, list), "Notes search failed")
    _print_step("Notes retrieval", f"{len(note_results)} result(s)")

    memory_saved = save_memory("My favorite integration test color is blue.")
    _print_step("Memory save", f"saved={memory_saved}")
    memory_results = search_memories("favorite color", top_k=3)
    _assert_true(isinstance(memory_results, list), "Memory search failed")
    _print_step("Memory retrieval", f"{len(memory_results)} result(s)")

    pdf_count = build_pdf_index()
    _print_step("PDF indexing", f"{pdf_count} new chunk(s)")
    pdf_results = search_documents("introduction", top_k=3)
    _assert_true(isinstance(pdf_results, list), "PDF search failed")
    _print_step("PDF search", f"{len(pdf_results)} result(s)")

    code_files, code_chunks = build_code_index(ROOT)
    _print_step("Code indexing", f"{code_files} file(s), {code_chunks} chunk(s)")
    code_results = search_code("load_model", top_k=3)
    _assert_true(isinstance(code_results, list), "Code search failed")
    _print_step("Code search", f"{len(code_results)} result(s)")

    print("\nFull system test completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"\n[FAIL] {exc}")
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"\n[FAIL] Unexpected error: {exc}")
        raise SystemExit(1) from exc
