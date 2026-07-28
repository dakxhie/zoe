"""Smoke test for the Zoe tool router."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.router import route_query

TEST_CASES: tuple[tuple[str, str], ...] = (
    ("What is my favorite color?", "memory"),
    ("Summarize Chapter 2.", "pdf"),
    ("Find generate_response().", "code"),
    ("Tell me about my notes.", "notes"),
    ("Hello!", "chat"),
)


def main() -> None:
    """Run tool routing examples and verify expected routes."""
    for query, expected in TEST_CASES:
        result = route_query(query)
        status = "ok" if result == expected else "FAIL"
        print(f'{status}: "{query}" -> {result} (expected {expected})')
        if result != expected:
            raise SystemExit(1)

    print("\nTool routing tests passed.")


if __name__ == "__main__":
    main()
