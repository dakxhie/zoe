"""Smoke test for web retrieval pipeline.

Usage: python scripts/test_web_retriever.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.retriever import retrieve_web_context

TEST_QUERY = "latest Python programming news"
PREVIEW_CHARS = 1500


def main() -> None:
    """Run web retrieval and print a context preview."""
    context = retrieve_web_context(TEST_QUERY, max_pages=3)

    print("Character count")
    print(len(context))
    print()
    print("First 1500 characters")
    print(context[:PREVIEW_CHARS])

    if not context:
        print("\nWeb retrieval returned no context (network or rate limit may apply).")
        return

    print("\nWeb retrieval test completed.")


if __name__ == "__main__":
    main()
