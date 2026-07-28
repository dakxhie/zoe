"""Pytest coverage for empty-index direct responses in the pipeline."""

from __future__ import annotations

from unittest.mock import patch

from brain.pipeline import generate_response
from core.index_status import EMPTY_INDEX_MESSAGES


@patch("brain.pipeline._record_exchange")
@patch("brain.pipeline.load_model")
@patch("brain.pipeline.run_project_analysis", return_value=(False, ""))
@patch("brain.pipeline.execute_tool", return_value=(False, ""))
@patch("brain.pipeline._try_save_memory", return_value=False)
@patch("brain.pipeline.get_empty_index_response", return_value=EMPTY_INDEX_MESSAGES["notes"])
def test_generate_response_returns_empty_index_message_without_loading_model(
    _mock_save: object,
    _mock_tool: object,
    _mock_analysis: object,
    mock_load_model: object,
    _mock_record: object,
) -> None:
    """Return empty-index guidance before loading the language model."""
    reply = generate_response("Tell me about my notes.")

    assert reply == EMPTY_INDEX_MESSAGES["notes"]
    mock_load_model.assert_not_called()
