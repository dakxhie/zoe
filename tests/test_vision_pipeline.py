"""Pytest coverage for vision pipeline behavior."""

from __future__ import annotations

from unittest.mock import patch

from PIL import Image

from vision.pipeline import _build_combined_context, analyze_image


def test_build_combined_context_uses_caption_when_ocr_empty() -> None:
    """Return caption-only context when OCR is empty."""
    combined = _build_combined_context("A dog in a park", "")

    assert "A dog in a park" in combined
    assert "Extracted Text:" in combined


def test_build_combined_context_uses_ocr_when_caption_empty() -> None:
    """Return OCR-only context when caption is empty."""
    combined = _build_combined_context("", "Receipt total $12.50")

    assert "Receipt total $12.50" in combined
    assert "Image Description:" in combined


def test_build_combined_context_empty_when_both_fail() -> None:
    """Return empty context only when both caption and OCR fail."""
    assert _build_combined_context("", "") == ""


def test_analyze_image_returns_partial_results() -> None:
    """Keep partial analysis when one vision step fails."""
    image = Image.new("RGB", (32, 32), color="blue")

    with patch("vision.pipeline.load_image", return_value=image), patch(
        "vision.pipeline._run_caption",
        return_value="A blue square",
    ), patch(
        "vision.pipeline._run_ocr",
        return_value="",
    ):
        result = analyze_image("sample.png")

    assert result["caption"] == "A blue square"
    assert result["ocr"] == ""
    assert result["combined_context"]
