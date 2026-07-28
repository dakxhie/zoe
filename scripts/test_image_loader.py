"""Smoke test for Zoe image loading.

Usage: python scripts/test_image_loader.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.loader import VisionLoaderError, image_info, load_image


def main() -> None:
    """Load an image and print its metadata."""
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/test_image_loader.py <image-path>")

    image_path = sys.argv[1]

    try:
        image = load_image(image_path)
        info = image_info(image_path)
    except VisionLoaderError as exc:
        raise SystemExit(str(exc)) from exc

    print("Filename")
    print(info["filename"])
    print()
    print("Resolution")
    print(f"{info['width']} x {info['height']}")
    print()
    print("Mode")
    print(info["mode"])
    print()
    print("Format")
    print(info["format"])

    if image.mode != "RGB":
        raise SystemExit(f"Expected RGB mode, got {image.mode}")

    print("\nImage loader test completed.")


if __name__ == "__main__":
    main()
