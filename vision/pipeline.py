"""Unified vision pipeline for Zoe AI."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

from core.text_utils import matches_any, normalize_text
from vision.caption import describe_loaded_image
from vision.loader import VisionLoaderError, load_image
from vision.ocr import extract_text_from_image

logger = logging.getLogger(__name__)

OCR_PRIORITY_PHRASES: tuple[str, ...] = (
    "read",
    "text",
    "ocr",
    "document",
    "receipt",
    "screenshot",
)

CAPTION_PRIORITY_PHRASES: tuple[str, ...] = (
    "describe",
    "photo",
    "picture",
    "image",
    "what is",
)


def _execution_mode(prompt: str) -> str:
    """Choose whether to prioritize OCR, caption, or both."""
    normalized = normalize_text(prompt)
    ocr_priority = matches_any(normalized, OCR_PRIORITY_PHRASES)
    caption_priority = matches_any(normalized, CAPTION_PRIORITY_PHRASES)

    if ocr_priority and not caption_priority:
        return "ocr_first"
    if caption_priority and not ocr_priority:
        return "caption_first"
    return "both"


def _build_metadata(image_path: str, image: Image.Image) -> dict[str, str | int]:
    """Build image metadata from a loaded image."""
    path = Path(image_path).expanduser()
    return {
        "filename": path.name,
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "format": (image.format or path.suffix.lstrip(".")).upper(),
    }


def _empty_metadata(image_path: str) -> dict[str, str | int]:
    """Build empty metadata when image loading fails."""
    path = Path(image_path).expanduser()
    return {
        "filename": path.name,
        "width": 0,
        "height": 0,
        "mode": "",
        "format": path.suffix.lstrip(".").upper(),
    }


def _build_combined_context(caption: str, ocr: str) -> str:
    """Merge caption and OCR output into one context string."""
    caption_text = caption.strip()
    ocr_text = ocr.strip()

    if not caption_text and not ocr_text:
        return ""

    return (
        f"Image Description:\n\n{caption_text}\n\n"
        f"Extracted Text:\n\n{ocr_text}"
    ).strip()


def _run_caption(image: Image.Image) -> str:
    """Generate an image caption without raising."""
    try:
        return describe_loaded_image(image)
    except Exception as exc:
        logger.warning("Caption step failed: %s", exc)
        return ""


def _run_ocr(image: Image.Image) -> str:
    """Extract OCR text without raising."""
    try:
        return extract_text_from_image(image)
    except Exception as exc:
        logger.warning("OCR step failed: %s", exc)
        return ""


def analyze_image(image_path: str, prompt: str = "") -> dict[str, str | dict[str, str | int]]:
    """Analyze an image with captioning and OCR in one unified call."""
    try:
        image = load_image(image_path)
    except VisionLoaderError as exc:
        logger.warning("Vision pipeline image load failed: %s", exc)
        return {
            "caption": "",
            "ocr": "",
            "combined_context": "",
            "metadata": _empty_metadata(image_path),
        }
    except Exception as exc:
        logger.warning("Unexpected vision pipeline image load failure: %s", exc)
        return {
            "caption": "",
            "ocr": "",
            "combined_context": "",
            "metadata": _empty_metadata(image_path),
        }

    metadata = _build_metadata(image_path, image)
    mode = _execution_mode(prompt)

    caption = ""
    ocr = ""

    if mode == "ocr_first":
        ocr = _run_ocr(image)
        caption = _run_caption(image)
    elif mode == "caption_first":
        caption = _run_caption(image)
        ocr = _run_ocr(image)
    else:
        caption = _run_caption(image)
        ocr = _run_ocr(image)

    return {
        "caption": caption,
        "ocr": ocr,
        "combined_context": _build_combined_context(caption, ocr),
        "metadata": metadata,
    }
