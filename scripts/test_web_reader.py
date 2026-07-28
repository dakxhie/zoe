"""Smoke test for webpage reading and text extraction."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.reader import read_webpage
from web.search import search_web

TEST_QUERY = "Python programming"
PREVIEW_CHARS = 1000


def main() -> None:
    """Search the web and read the first result."""
    results = search_web(TEST_QUERY, max_results=1)

    if not results:
        print("No search results found.")
        raise SystemExit(1)

    first_result = results[0]
    title = first_result.get("title", "")
    url = first_result.get("url", "")

    if not url:
        print("First search result has no URL.")
        raise SystemExit(1)

    page_text = read_webpage(url)

    print("Title")
    print(title)
    print()
    print("URL")
    print(url)
    print()
    print("Character count")
    print(len(page_text))
    print()
    print("First 1000 characters")
    print(page_text[:PREVIEW_CHARS])

    if not page_text:
        print("\nWeb reader returned no text.")
        raise SystemExit(1)

    print("\nWeb reader test completed.")


if __name__ == "__main__":
    main()
