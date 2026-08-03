"""Voice command routing tests."""

from __future__ import annotations

from unittest.mock import patch

from voice.commands import VoiceAction, try_voice_command


def test_open_settings_command() -> None:
    result = try_voice_command("Open settings")
    assert result.handled is True
    assert result.action == VoiceAction.OPEN_SETTINGS


def test_datetime_tool_without_llm() -> None:
    with patch("voice.commands.execute_tool", return_value=(True, "12:00 PM")):
        result = try_voice_command("What time is it in Tokyo?")
    assert result.handled is True
    assert "12:00" in result.response


@patch("brain.pipeline.generate_response", return_value="LLM reply")
def test_llm_fallback(mock_generate) -> None:
    from voice.commands import generate_voice_response

    assert generate_voice_response("Tell me a joke") == "LLM reply"
    mock_generate.assert_called_once()
