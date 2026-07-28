"""Smoke test for code search."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codebase.retriever import CodeRetrieverError, search_code

SEARCH_QUERIES: tuple[str, ...] = (
    "load_model",
    "save_memory",
    "build_code_index",
)


def _print_results(query: str, results: list[dict[str, str]]) -> None:
    """Print code search results for one query."""
    print(f'Search: "{query}"')

    if not results:
        print("Matches: (none)\n")
        return

    print("Matches:")
    for result in results:
        preview = result["content"][:200]
        print(
            f"- {result['path']} [{result['language']}]: "
            f"{preview}"
        )
    print()


def main() -> None:
    """Search indexed code chunks and print readable output."""
    try:
        for query in SEARCH_QUERIES:
            results = search_code(query, top_k=3)
            _print_results(query, results)
    except CodeRetrieverError as exc:
        print(f"Code search test failed: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
