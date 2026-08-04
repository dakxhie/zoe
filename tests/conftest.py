"""Shared pytest configuration for Zoe AI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.headless import (  # noqa: E402
    HEADLESS_SKIP_REASON,
    VOICE_OPTIONAL_SKIP_REASON,
    configure_qt_platform_for_tests,
    is_headless_environment,
)


def pytest_configure(config: pytest.Config) -> None:
    """Register markers and configure Qt before collection imports widgets."""
    config.addinivalue_line("markers", "gui: Qt widget tests (skipped on headless CI/Colab)")
    config.addinivalue_line(
        "markers",
        "voice_optional: requires optional voice packages from requirements-voice.txt",
    )
    configure_qt_platform_for_tests()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-mark tests that depend on the shared qapp fixture."""
    for item in items:
        if "qapp" in item.fixturenames:
            item.add_marker(pytest.mark.gui)


@pytest.fixture(scope="session")
def qapp():
    """Shared QApplication singleton for desktop and voice widget tests."""
    if is_headless_environment():
        pytest.skip(HEADLESS_SKIP_REASON)

    pytest.importorskip("PySide6")
    configure_qt_platform_for_tests()

    from PySide6.QtWidgets import QApplication

    existing = QApplication.instance()
    if existing is not None:
        yield existing
        return

    application = QApplication([])
    application.setQuitOnLastWindowClosed(False)
    yield application

    # Do not call application.quit() — other tests may still use the singleton.


@pytest.fixture
def requires_voice_optional() -> None:
    """Skip when optional voice packages are not installed."""
    from voice.deps import voice_stt_available, voice_tts_available

    if voice_stt_available() and voice_tts_available():
        return
    pytest.skip(VOICE_OPTIONAL_SKIP_REASON)


@pytest.fixture(autouse=True)
def _zoe_test_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep tests from writing into the developer's real config paths."""
    monkeypatch.setenv("ANONYMIZED_TELEMETRY", "False")
    if not os.environ.get("ZOE_TEST_DATA"):
        monkeypatch.setenv("ZOE_TEST_DATA", str(tmp_path / "zoe_test_data"))
