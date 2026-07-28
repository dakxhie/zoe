"""Smoke test for PDF document search.

Usage: python scripts/test_pdf_search.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pdf.retriever import PDFRetrieverError, search_documents

SEARCH_QUERIES: tuple[str, ...] = (
    "introduction",
    "goals",
    "chunking",
)


def _print_results(query: str, results: list[dict[str, object]]) -> None:
    """Print PDF search results for one query."""
    print(f'Search: "{query}"')

    if not results:
        print("Matches: (none)\n")
        return

    print("Matches:")
    for result in results:
        preview = str(result["content"])[:200]
        print(
            f"- {result['filename']} [chunk {result['chunk']}]: "
            f"{preview}"
        )
    print()


def main() -> None:
    """Search indexed PDF chunks and print readable output."""
    try:
        for query in SEARCH_QUERIES:
            results = search_documents(query, top_k=3)
            _print_results(query, results)
    except PDFRetrieverError as exc:
        print(f"PDF search test failed: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
