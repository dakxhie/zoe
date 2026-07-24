"""Smoke test for the Zoe RAG retrieval pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.retriever import RetrieverError, build_index, search

TEST_QUERY = "favorite programming language"


def _print_results(results: list[dict[str, str]]) -> None:
    """Print retrieved document filenames and content."""
    if not results:
        print("No documents found.")
        return

    for index, result in enumerate(results, start=1):
        print(f"Result {index}")
        print(f"Filename: {result['filename']}")
        print(f"Content:\n{result['content']}\n")


def main() -> None:
    """Build the note index and run a sample search query."""
    try:
        indexed_count = build_index()
        print(f"Indexed {indexed_count} new document(s).\n")

        results = search(TEST_QUERY, top_k=3)
        print(f'Search query: "{TEST_QUERY}"\n')
        _print_results(results)
    except RetrieverError as exc:
        print(f"RAG test failed: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
