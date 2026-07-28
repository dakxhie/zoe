"""Smoke test for code indexing.

Usage: python scripts/test_code_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codebase.indexer import build_code_index


def main() -> None:
    """Build the code index for the Zoe project."""
    indexed_files, indexed_chunks = build_code_index(ROOT)
    print(f"Indexed files: {indexed_files}")
    print(f"Indexed chunks: {indexed_chunks}")


if __name__ == "__main__":
    main()
