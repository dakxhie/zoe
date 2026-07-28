"""Smoke test for DuckDuckGo web search."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.search import search_web

TEST_QUERY = "Python"


def _print_results(query: str, results: list[dict[str, str]]) -> None:
    """Print search results in a readable format."""
    print(f"Search:\n{query}\n")

    if not results:
        print("No results found.")
        return

    for index, result in enumerate(results, start=1):
        print(f"{index}.")
        print("Title:")
        print(result.get("title", ""))
        print()
        print("URL:")
        print(result.get("url", ""))
        print()
        print("Snippet:")
        print(result.get("body", ""))
        print()


def main() -> None:
    """Run a sample web search query."""
    results = search_web(TEST_QUERY, max_results=5)
    _print_results(TEST_QUERY, results)

    if not results:
        print("Web search returned no results (network or rate limit may apply).")
        return

    print("Web search test completed.")


if __name__ == "__main__":
    main()
