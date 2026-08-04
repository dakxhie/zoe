"""Voice manager tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from tests.headless import skip_if_headless_gui

skip_if_headless_gui()

pytest.importorskip("PySide6")

from voice.manager import VoiceManager, VoiceState
from voice.settings import VoiceSettings


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


@patch("voice.deps.voice_capture_available", return_value=True)
@patch("voice.manager._ListenThread")
def test_toggle_push_to_talk_starts_listener(mock_thread, _mock_capture, qapp) -> None:
    settings = VoiceSettings(enabled=True)
    manager = VoiceManager(settings)
    instance = MagicMock()
    mock_thread.return_value = instance
    manager.toggle_push_to_talk()
    instance.start.assert_called_once()
