"""Smoke test for the unified Zoe vision pipeline.

Usage: python scripts/test_vision_pipeline.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.pipeline import analyze_image

PREVIEW_CHARS = 500


def main() -> None:
    """Run unified vision analysis on an image."""
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/test_vision_pipeline.py <image-path>")

    image_path = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else ""
    result = analyze_image(image_path, prompt=prompt)

    print("Metadata")
    print(json.dumps(result["metadata"], indent=2))
    print()
    print("Caption")
    print(result["caption"] if result["caption"] else "(empty)")
    print()
    print("OCR length")
    print(len(result["ocr"]))
    print()
    print("Combined context preview")
    preview = result["combined_context"][:PREVIEW_CHARS]
    print(preview if preview else "(empty)")

    print("\nVision pipeline test completed.")


if __name__ == "__main__":
    main()
