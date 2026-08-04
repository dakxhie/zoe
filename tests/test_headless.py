"""Tests for headless environment detection."""

from __future__ import annotations

import os
from unittest.mock import patch

from tests.headless import is_headless_environment


def test_github_actions_is_headless() -> None:
    with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
        assert is_headless_environment() is True


def test_force_gui_overrides_ci() -> None:
    env = {"GITHUB_ACTIONS": "true", "ZOE_FORCE_GUI_TESTS": "1"}
    with patch.dict(os.environ, env, clear=False):
        assert is_headless_environment() is False


def test_colab_release_tag_is_headless() -> None:
    with patch.dict(os.environ, {"COLAB_RELEASE_TAG": "release_2024"}, clear=False):
        assert is_headless_environment() is True
