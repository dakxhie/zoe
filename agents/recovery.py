"""Recovery and fallback helpers for agent tool execution."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def run_with_recovery(
    label: str,
    operation: Callable[[], T],
    *,
    fallback: Callable[[], T] | None = None,
    warning_message: str | None = None,
) -> tuple[T | None, str | None]:
    """Run an operation and optionally fall back without aborting the plan."""
    try:
        return operation(), None
    except Exception as exc:
        message = warning_message or f"{label} failed: {exc}"
        logger.warning(message)
        if fallback is not None:
            try:
                return fallback(), message
            except Exception as fallback_exc:
                logger.warning("%s fallback failed: %s", label, fallback_exc)
        return None, message


def retry_once(label: str, operation: Callable[[], T]) -> tuple[T | None, str | None]:
    """Retry an operation once after failure."""
    for attempt in (1, 2):
        try:
            return operation(), None
        except Exception as exc:
            if attempt == 1:
                logger.debug("%s failed on attempt 1, retrying once: %s", label, exc)
                time.sleep(0.05)
                continue
            return None, f"{label} failed after retry: {exc}"
    return None, f"{label} failed"


def vision_fallback_caption_only(vision_result: dict[str, object]) -> dict[str, object]:
    """Prefer caption when OCR fails."""
    caption = str(vision_result.get("caption", "")).strip()
    ocr = str(vision_result.get("ocr", "")).strip()
    if caption and not ocr:
        vision_result = dict(vision_result)
        vision_result["combined_context"] = f"Image Description:\n\n{caption}"
    return vision_result


def vision_fallback_ocr_only(vision_result: dict[str, object]) -> dict[str, object]:
    """Prefer OCR when caption fails."""
    caption = str(vision_result.get("caption", "")).strip()
    ocr = str(vision_result.get("ocr", "")).strip()
    if ocr and not caption:
        vision_result = dict(vision_result)
        vision_result["combined_context"] = f"Extracted Text:\n\n{ocr}"
    return vision_result
