"""Desktop startup tests."""

from __future__ import annotations

import importlib


def test_desktop_app_module_imports() -> None:
    """Desktop entry module imports without starting Qt event loop."""
    module = importlib.import_module("desktop.app")
    assert hasattr(module, "main")


def test_theme_module_exports_styles() -> None:
    """Theme module provides dark and light stylesheets."""
    from desktop.theme import DARK_STYLESHEET, LIGHT_STYLESHEET, apply_theme

    assert "QMainWindow" in DARK_STYLESHEET
    assert "QMainWindow" in LIGHT_STYLESHEET
    assert callable(apply_theme)
