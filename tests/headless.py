"""Detect headless environments where Qt GUI tests must not run."""

from __future__ import annotations

import os
import sys


HEADLESS_SKIP_REASON = "Desktop GUI tests skipped on headless environment"
VOICE_OPTIONAL_SKIP_REASON = "Optional voice dependencies not installed"


def is_headless_environment() -> bool:
    """Return True when there is no usable display for Qt widget tests."""
    if os.environ.get("ZOE_FORCE_GUI_TESTS", "").strip() in {"1", "true", "yes"}:
        return False

    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        return True

    if os.environ.get("CI", "").lower() == "true":
        if not os.environ.get("DISPLAY", "").strip() and not os.environ.get("WAYLAND_DISPLAY", "").strip():
            return True

    if os.environ.get("COLAB_RELEASE_TAG") or os.environ.get("COLAB_GPU"):
        return True

    if "google.colab" in sys.modules:
        return True

    if sys.platform.startswith("linux"):
        display = os.environ.get("DISPLAY", "").strip()
        wayland = os.environ.get("WAYLAND_DISPLAY", "").strip()
        if not display and not wayland:
            if _is_wsl() or os.environ.get("RUNNER_OS") == "Linux":
                return True

    return False


def _is_wsl() -> bool:
    try:
        with open("/proc/version", encoding="utf-8", errors="ignore") as handle:
            return "microsoft" in handle.read().lower()
    except OSError:
        return False


def configure_qt_platform_for_tests() -> None:
    """Use offscreen Qt platform when running GUI tests without a native display."""
    if is_headless_environment():
        return
    if sys.platform.startswith("linux") and not os.environ.get("QT_QPA_PLATFORM"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def skip_if_headless_gui() -> None:
    """Module-level skip before importing Qt widgets."""
    import pytest

    if is_headless_environment():
        pytest.skip(HEADLESS_SKIP_REASON, allow_module_level=True)


def skip_if_voice_optional_unavailable() -> None:
    """Module-level skip when optional voice stack is not installed."""
    import pytest

    from voice.deps import voice_stt_available, voice_tts_available

    if voice_stt_available() and voice_tts_available():
        return
    pytest.skip(VOICE_OPTIONAL_SKIP_REASON, allow_module_level=True)
