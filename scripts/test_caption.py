"""Smoke test for Zoe image captioning.

Usage: python scripts/test_caption.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.caption import describe_image


def main() -> None:
    """Generate and print a caption for an image."""
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/test_caption.py <image-path>")

    image_path = sys.argv[1]
    caption = describe_image(image_path)

    print("Caption:")
    print(caption if caption else "(empty)")

    print("\nCaption test completed.")


if __name__ == "__main__":
    main()
