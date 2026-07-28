"""Smoke test for conversation memory retrieval.

Usage: python scripts/test_memory_retriever.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory.retriever import MemoryRetrieverError, search_memories

SEARCH_QUERIES: tuple[str, ...] = (
    "favorite color",
    "favorite food",
    "building",
)


def _print_results(query: str, results: list[dict[str, str]]) -> None:
    """Print memory matches for one search query."""
    print(f'Search: "{query}"')

    if not results:
        print("Matches: (none)\n")
        return

    print("Matches:")
    for result in results:
        print(f"- [{result['created_at']}] {result['content']}")
    print()


def main() -> None:
    """Search stored conversation memories and print the matches."""
    try:
        for query in SEARCH_QUERIES:
            results = search_memories(query, top_k=3)
            _print_results(query, results)
    except MemoryRetrieverError as exc:
        print(f"Memory retriever test failed: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
