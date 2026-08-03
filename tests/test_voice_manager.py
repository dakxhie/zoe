"""Voice manager tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

pytest.importorskip("PySide6")

from voice.manager import VoiceManager, VoiceState
from voice.settings import VoiceSettings


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_voice_manager_starts_idle(qapp) -> None:
    settings = VoiceSettings(enabled=True)
    manager = VoiceManager(settings)
    assert manager.state == VoiceState.IDLE


def test_start_listening_disabled_emits_error(qapp) -> None:
    settings = VoiceSettings(enabled=False)
    manager = VoiceManager(settings)
    errors: list[str] = []
    manager.error_occurred.connect(errors.append)
    manager.start_listening()
    assert errors


@patch("voice.manager._ListenThread")
def test_toggle_push_to_talk_starts_listener(mock_thread, qapp) -> None:
    settings = VoiceSettings(enabled=True)
    manager = VoiceManager(settings)
    instance = MagicMock()
    mock_thread.return_value = instance
    manager.toggle_push_to_talk()
    instance.start.assert_called_once()
