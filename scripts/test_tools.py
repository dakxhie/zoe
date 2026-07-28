"""Smoke test for tool execution.

Usage: python scripts/test_tools.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.executor import execute_tool

TEST_CASES: tuple[tuple[str, bool], ...] = (
    ("2+2", True),
    ("10*(5+2)", True),
    ("Current time", True),
    ("Today's date", True),
    ("Hello", False),
)


def main() -> None:
    """Run tool execution examples."""
    for query, should_handle in TEST_CASES:
        handled, result = execute_tool(query)
        status = "ok" if handled == should_handle else "FAIL"
        print(f'{status}: "{query}" -> handled={handled}, result={result!r}')

        if handled != should_handle:
            raise SystemExit(1)

        if should_handle and not result:
            raise SystemExit(1)

    print("\nTool execution tests passed.")


if __name__ == "__main__":
    main()
