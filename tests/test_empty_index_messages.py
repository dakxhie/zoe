"""Pytest coverage for empty-index user responses."""

from __future__ import annotations

from unittest.mock import patch

from brain.context import _build_merged_context, get_empty_index_response
from core.index_status import EMPTY_INDEX_MESSAGES


@patch("brain.context.collection_count", return_value=0)
def test_empty_notes_index_message(_mock_count: object) -> None:
    """Return the notes indexing guidance when the notes index is empty."""
    query = "Tell me about my notes."
    assert get_empty_index_response(query) == EMPTY_INDEX_MESSAGES["notes"]
    assert _build_merged_context(query) == EMPTY_INDEX_MESSAGES["notes"]


@patch("brain.context.collection_count", return_value=0)
def test_empty_pdf_index_message(_mock_count: object) -> None:
    """Return the PDF indexing guidance when the PDF index is empty."""
    query = "Summarize Chapter 2 from my pdf."
    assert get_empty_index_response(query) == EMPTY_INDEX_MESSAGES["pdf"]
    assert _build_merged_context(query) == EMPTY_INDEX_MESSAGES["pdf"]


@patch("brain.context.collection_count", return_value=0)
def test_empty_code_index_message(_mock_count: object) -> None:
    """Return the code indexing guidance when the code index is empty."""
    query = "Explain generate_response()."
    assert get_empty_index_response(query) == EMPTY_INDEX_MESSAGES["code"]
    assert _build_merged_context(query) == EMPTY_INDEX_MESSAGES["code"]


@patch("brain.context.collection_count", return_value=3)
@patch("brain.context._retrieve_notes", return_value=[{"content": "note text"}])
def test_nonempty_index_skips_empty_message(
    _mock_retrieve: object,
    _mock_count: object,
) -> None:
    """Keep normal retrieval when the index contains documents."""
    query = "Tell me about my notes."
    assert get_empty_index_response(query) is None
    assert "note text" in _build_merged_context(query)
