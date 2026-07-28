"""Smoke test for PDF indexing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pdf.indexer import build_pdf_index


def main() -> None:
    """Build the PDF index and print the number of indexed chunks."""
    indexed_chunks = build_pdf_index()
    print(f"Indexed PDF chunks: {indexed_chunks}")


if __name__ == "__main__":
    main()
