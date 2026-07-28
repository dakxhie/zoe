"""Pytest coverage for analysis pipeline integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agents.analyzer import run_project_analysis
from brain.context import _build_chat_messages
from brain.pipeline import generate_response


ANALYSIS_QUERY = "Analyze this Python project and tell me how to improve it."


def test_analysis_context_is_injected_into_system_prompt() -> None:
    """Always inject gathered analysis context into the prompt."""
    is_analysis, context = run_project_analysis(ANALYSIS_QUERY)

    assert is_analysis
    messages = _build_chat_messages(ANALYSIS_QUERY, [], analysis_context=context)
    system_message = messages[0]["content"]

    assert "Project Analysis" in system_message
    assert "README.md" in system_message
    assert "Do not ask the user for more files" in system_message


@patch("brain.pipeline._record_exchange")
@patch("brain.pipeline.generate_text", return_value="Analysis reply")
@patch("brain.pipeline.load_model")
@patch("brain.pipeline._try_save_memory", return_value=False)
@patch("brain.pipeline.execute_tool", return_value=(False, ""))
def test_generate_response_keeps_analysis_context(
    _execute_tool,
    _save_memory,
    load_model,
    _generate_text,
    _record_exchange,
) -> None:
    """Keep analysis context through the chat pipeline."""
    load_model.return_value = (MagicMock(), MagicMock())

    reply = generate_response(ANALYSIS_QUERY)

    assert reply == "Analysis reply"
    messages = _generate_text.call_args.args[2]
    assert "Project Analysis" in messages[0]["content"]


@patch("agents.analyzer.execute_project_analysis", return_value="")
def test_empty_analysis_context_is_logged(mock_execute) -> None:
    """Surface empty analysis context without crashing."""
    is_analysis, context = run_project_analysis(ANALYSIS_QUERY)

    assert is_analysis
    assert context.startswith("Plan:")
    mock_execute.assert_called_once()
