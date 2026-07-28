"""Smoke test for Zoe OCR.

Usage: python scripts/test_ocr.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.ocr import extract_text


def main() -> None:
    """Extract text from an image and print the result."""
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/test_ocr.py <image-path>")

    image_path = sys.argv[1]
    text = extract_text(image_path)

    print("Character count")
    print(len(text))
    print()
    print("Extracted text")
    print(text if text else "(empty)")

    print("\nOCR test completed.")


if __name__ == "__main__":
    main()
