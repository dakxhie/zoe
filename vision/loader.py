"""Image loading for Zoe AI."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp"})


class VisionLoaderError(RuntimeError):
    """Raised when an image cannot be loaded."""


def _resolve_path(path: str) -> Path:
    """Resolve and validate an image path."""
    image_path = Path(path).expanduser()

    if not image_path.exists():
        raise VisionLoaderError(f"Image file not found: {path}")

    if not image_path.is_file():
        raise VisionLoaderError(f"Path is not a file: {path}")

    extension = image_path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise VisionLoaderError(
            f"Unsupported image format '{extension}'. Supported formats: {supported}"
        )

    return image_path


def load_image(path: str) -> Image.Image:
    """Load an image from disk, correct orientation, and convert to RGB."""
    image_path = _resolve_path(path)

    try:
        with Image.open(image_path) as opened:
            oriented = ImageOps.exif_transpose(opened)
            rgb_image = oriented.convert("RGB")
            rgb_image.load()
            return rgb_image.copy()
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise VisionLoaderError(f"Failed to load image '{path}': {exc}") from exc


def image_info(path: str) -> dict[str, str | int]:
    """Return basic metadata for an image file."""
    image = load_image(path)
    image_path = _resolve_path(path)

    return {
        "filename": image_path.name,
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "format": (image.format or image_path.suffix.lstrip(".")).upper(),
    }
