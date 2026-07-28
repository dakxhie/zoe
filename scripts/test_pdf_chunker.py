"""Smoke test for PDF text chunking.

Usage: python scripts/test_pdf_chunker.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pdf.chunker import chunk_text

SAMPLE_TEXT = """Introduction

This is the first paragraph of a sample PDF document. It contains enough words
to demonstrate paragraph-aware chunking behavior.

This is the second paragraph. It should remain intact whenever possible and
should never be split in the middle of a word.

Goals

The chunker should produce deterministic overlapping chunks for indexing."""


def main() -> None:
    """Print chunk summaries for sample text."""
    chunks = chunk_text(SAMPLE_TEXT, chunk_size=120, overlap=30)

    print(f"Total chunks: {len(chunks)}\n")

    for chunk in chunks:
        print(f"Chunk ID: {chunk['chunk_id']}")
        print(f"Length: {len(chunk['text'])}")
        print(f"Text:\n{chunk['text']}\n")


if __name__ == "__main__":
    main()
