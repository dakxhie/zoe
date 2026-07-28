"""Smoke test for the smart retrieval pipeline."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import brain.context as context
import brain.model as model
from tools.router import route_query

TEST_CASES: tuple[tuple[str, str, str | None], ...] = (
    ("What is my favorite color?", "memory", "_retrieve_memories"),
    ("Summarize Chapter 1", "pdf", "_retrieve_documents"),
    ("Explain generate_response()", "code", "_retrieve_code"),
    ("Hello", "chat", None),
)

SAMPLE_RESULT = [{"content": "sample context"}]


def _run_pipeline_test(query: str, expected_tool: str, retrieve_function: str | None) -> None:
    """Verify routing and that only the expected retriever is used."""
    tool = route_query(query)
    assert tool == expected_tool, f'Expected tool "{expected_tool}", got "{tool}"'

    patches = {
        "_retrieve_memories": patch.object(context, "_retrieve_memories", return_value=SAMPLE_RESULT),
        "_retrieve_notes": patch.object(context, "_retrieve_notes", return_value=SAMPLE_RESULT),
        "_retrieve_documents": patch.object(context, "_retrieve_documents", return_value=SAMPLE_RESULT),
        "_retrieve_code": patch.object(context, "_retrieve_code", return_value=SAMPLE_RESULT),
    }

    with patches["_retrieve_memories"], patches["_retrieve_notes"], patches["_retrieve_documents"], patches["_retrieve_code"]:
        merged = model._build_merged_context(query)

        if retrieve_function is None:
            assert merged == "", f'Expected no context for query: "{query}"'
            context._retrieve_memories.assert_not_called()
            context._retrieve_notes.assert_not_called()
            context._retrieve_documents.assert_not_called()
            context._retrieve_code.assert_not_called()
            return

        assert merged != "", f'Expected context for query: "{query}"'

        called = {
            "_retrieve_memories": context._retrieve_memories.called,
            "_retrieve_notes": context._retrieve_notes.called,
            "_retrieve_documents": context._retrieve_documents.called,
            "_retrieve_code": context._retrieve_code.called,
        }

        assert called[retrieve_function], f"{retrieve_function} was not called"
        assert sum(called.values()) == 1, "More than one retriever was called"


def main() -> None:
    """Run smart retrieval pipeline checks."""
    for query, expected_tool, retrieve_function in TEST_CASES:
        _run_pipeline_test(query, expected_tool, retrieve_function)
        print(f'ok: "{query}" -> {expected_tool}')

    print("\nSmart retrieval pipeline tests passed.")


if __name__ == "__main__":
    main()
