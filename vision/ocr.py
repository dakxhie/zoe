"""Optical character recognition for Zoe AI."""

from __future__ import annotations

import logging
import re

from PIL import Image

from vision.loader import VisionLoaderError, load_image

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGES: tuple[str, ...] = ("en",)

_reader: object | None = None
_reader_languages: tuple[str, ...] | None = None


def _normalize_text(text: str) -> str:
    """Normalize OCR output whitespace."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t\f\v]+", " ", normalized)
    normalized = re.sub(r"\n[ \t]+", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    lines = [line.rstrip() for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def _get_reader(languages: tuple[str, ...] = DEFAULT_LANGUAGES) -> object | None:
    """Return a lazily initialized EasyOCR reader."""
    global _reader, _reader_languages

    try:
        import easyocr
    except ImportError:
        logger.warning("EasyOCR is not installed")
        return None

    if _reader is not None and _reader_languages == languages:
        return _reader

    try:
        _reader = easyocr.Reader(list(languages))
        _reader_languages = languages
    except Exception as exc:
        logger.warning("Failed to initialize EasyOCR reader: %s", exc)
        _reader = None
        _reader_languages = None
        return None

    return _reader


def _image_to_array(image: Image.Image):
    """Convert a PIL image to a NumPy array for EasyOCR."""
    import numpy as np

    rgb_image = image.convert("RGB")
    return np.array(rgb_image)


def extract_text_from_image(image: Image.Image) -> str:
    """Extract text from a loaded PIL image."""
    reader = _get_reader()
    if reader is None:
        return ""

    try:
        results = reader.readtext(_image_to_array(image))
    except Exception as exc:
        logger.warning("OCR failed on image: %s", exc)
        return ""

    if not results:
        return ""

    lines: list[str] = []
    for item in results:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        text = str(item[1]).strip()
        if text:
            lines.append(text)

    return _normalize_text("\n".join(lines))


def extract_text(image_path: str) -> str:
    """Extract text from an image file path."""
    try:
        image = load_image(image_path)
    except VisionLoaderError as exc:
        logger.warning("OCR image load failed: %s", exc)
        return ""
    except Exception as exc:
        logger.warning("Unexpected OCR image load failure: %s", exc)
        return ""

    return extract_text_from_image(image)
