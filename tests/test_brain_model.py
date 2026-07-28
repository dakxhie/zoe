"""Pytest coverage for brain module public API."""

from __future__ import annotations

from brain.model import ModelLoadError, generate_response, load_model


def test_public_api_exports() -> None:
    """Expose the expected public entry points."""
    assert callable(generate_response)
    assert callable(load_model)
    assert issubclass(ModelLoadError, RuntimeError)
