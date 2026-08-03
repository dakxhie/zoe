"""Pytest coverage for empty-index direct responses in the pipeline."""

from __future__ import annotations

from unittest.mock import patch

from brain.pipeline import generate_response
from core.index_status import EMPTY_INDEX_MESSAGES


from agents.orchestrator import OrchestratedTurn


@patch("brain.pipeline._record_exchange")
@patch("brain.pipeline.load_model")
@patch("agents.orchestrator.orchestrate_chat_turn")
@patch("brain.pipeline.execute_tool", return_value=(False, ""))
@patch("brain.pipeline._try_save_memory", return_value=False)
def test_generate_response_returns_empty_index_message_without_loading_model(
    _mock_save: object,
    _mock_tool: object,
    mock_orchestrate: object,
    mock_load_model: object,
    _mock_record: object,
) -> None:
    """Return empty-index guidance before loading the language model."""
    mock_orchestrate.return_value = OrchestratedTurn(
        empty_index_response=EMPTY_INDEX_MESSAGES["notes"],
    )

    reply = generate_response("Tell me about my notes.")

    assert reply == EMPTY_INDEX_MESSAGES["notes"]
    mock_load_model.assert_not_called()
