"""Smoke test for vision chat integration.

Usage: python scripts/test_chat_vision.py
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.context import _build_chat_messages, build_vision_context
from brain.pipeline import generate_image_response
from tools.router import extract_image_path, route_query

SAMPLE_VISION_RESULT = {
    "caption": "a computer screen with code on it",
    "ocr": "SyntaxError: invalid syntax",
    "combined_context": (
        "Image Description:\n\n"
        "a computer screen with code on it\n\n"
        "Extracted Text:\n\n"
        "SyntaxError: invalid syntax"
    ),
    "metadata": {
        "filename": "screenshot.png",
        "width": 800,
        "height": 600,
        "mode": "RGB",
        "format": "PNG",
    },
}


def _test_router() -> None:
    """Route image requests to the vision tool."""
    query = "What error is shown in screenshot.png?"
    if route_query(query) != "vision":
        raise SystemExit(f'Expected vision route, got "{route_query(query)}"')

    image_path = extract_image_path(query)
    if image_path != "screenshot.png":
        raise SystemExit(f'Expected screenshot.png, got "{image_path}"')

    print("ok: router")


def _test_context() -> None:
    """Build vision context and chat messages."""
    context = build_vision_context(SAMPLE_VISION_RESULT)
    if "Image Description:" not in context:
        raise SystemExit("Vision context missing image description")
    if "Extracted Text:" not in context:
        raise SystemExit("Vision context missing extracted text")
    if "Metadata:" not in context:
        raise SystemExit("Vision context missing metadata")

    messages = _build_chat_messages(
        "Explain this screenshot.",
        [],
        vision_context=context,
    )
    system_message = messages[0]["content"]
    if "## Vision Context" not in system_message:
        raise SystemExit("Vision system prompt missing heading")

    print("ok: context")


def _test_pipeline() -> None:
    """Generate an image response using mocked vision and LLM steps."""
    with patch("brain.pipeline._retrieve_vision", return_value=SAMPLE_VISION_RESULT), patch(
        "brain.pipeline.load_model",
        return_value=(object(), object()),
    ), patch(
        "brain.pipeline.generate_text",
        return_value="The screenshot shows a syntax error.",
    ), patch("brain.pipeline.get_history", return_value=[]), patch(
        "brain.pipeline._record_exchange"
    ):
        reply = generate_image_response("screenshot.png", "Explain this screenshot.")

    if "syntax error" not in reply.lower():
        raise SystemExit("Expected pipeline to return mocked LLM reply")

    print("ok: pipeline")


def _test_direct_mode() -> None:
    """Run CLI direct mode without loading the LLM."""
    from cli.main import image

    with patch("cli.main.analyze_image", return_value=SAMPLE_VISION_RESULT), patch(
        "cli.main.generate_image_response",
        side_effect=AssertionError("LLM should not load in direct mode"),
    ):
        stdout = StringIO()
        with patch("sys.stdout", stdout):
            image("screenshot.png")

    output = stdout.getvalue()
    if "Caption" not in output or "OCR" not in output or "Metadata" not in output:
        raise SystemExit("Direct mode output missing expected sections")

    print("ok: direct mode")


def main() -> None:
    """Run vision chat integration checks."""
    _test_router()
    _test_context()
    _test_pipeline()
    _test_direct_mode()
    print("\nVision chat integration tests passed.")


if __name__ == "__main__":
    main()
