"""Smoke test for PDF text extraction."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pdf.loader import PDFLoaderError, load_pdfs

PREVIEW_LENGTH = 200


def _print_document(document: dict[str, str]) -> None:
    """Print summary information for one loaded PDF."""
    text = document["text"]
    preview = text[:PREVIEW_LENGTH]

    print(f"Filename: {document['filename']}")
    print(f"Character count: {len(text)}")
    print(f"First {PREVIEW_LENGTH} characters:\n{preview}\n")


def main() -> None:
    """Load every PDF and print a short text preview."""
    try:
        documents = load_pdfs()
    except PDFLoaderError as exc:
        print(f"PDF loader test failed: {exc}")
        raise SystemExit(1) from exc

    if not documents:
        print("No PDFs with extractable text were found in data/pdfs/.")
        return

    for document in documents:
        _print_document(document)


if __name__ == "__main__":
    main()
