"""Smoke test for webpage cache hits and downloads.

Usage: python scripts/test_web_cache.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.cache import clear_web_cache
from web.retriever import retrieve_web_context

TEST_QUERY = "Python programming"
MAX_PAGES = 2


def main() -> None:
    """Run web retrieval twice to verify cache behavior."""
    clear_web_cache()

    print("=== First retrieval ===")
    first_context = retrieve_web_context(TEST_QUERY, max_pages=MAX_PAGES)
    print(f"\nCharacter count: {len(first_context)}")

    print("\n=== Second retrieval ===")
    second_context = retrieve_web_context(TEST_QUERY, max_pages=MAX_PAGES)
    print(f"\nCharacter count: {len(second_context)}")

    if not first_context and not second_context:
        print("\nWeb cache test returned no context (network or rate limit may apply).")
        return

    print("\nWeb cache test completed.")


if __name__ == "__main__":
    main()
