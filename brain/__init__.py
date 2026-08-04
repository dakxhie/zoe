"""Model loading, context building, and chat generation for Zoe AI."""

from __future__ import annotations

from typing import Any

__all__ = [
    "ModelLoadError",
    "generate_image_response",
    "generate_response",
    "generate_text",
    "is_model_loaded",
    "load_model",
]


def __getattr__(name: str) -> Any:
    if name in {
        "ModelLoadError",
        "generate_text",
        "is_model_loaded",
        "load_model",
    }:
        from brain import generation as generation_module

        return getattr(generation_module, name)
    if name in {"generate_image_response", "generate_response"}:
        from brain import pipeline as pipeline_module

        return getattr(pipeline_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
