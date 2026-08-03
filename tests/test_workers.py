"""Worker unit tests for Zoe Desktop."""

from __future__ import annotations

from unittest.mock import patch

from desktop.workers import WorkerResult, run_doctor_report, run_index_notes


def test_run_index_notes_calls_backend() -> None:
    """Notes indexing worker delegates to rag.retriever.build_index."""
    with patch("rag.retriever.build_index", return_value=12) as mock_build:
        assert run_index_notes() == 12
        mock_build.assert_called_once()


def test_run_doctor_report_returns_report() -> None:
    """Doctor worker returns a structured report object."""
    with patch("core.doctor.run_doctor") as mock_doctor:
        mock_doctor.return_value = object()
        assert run_doctor_report() is mock_doctor.return_value
        mock_doctor.assert_called_once()


def test_worker_result_container() -> None:
    """WorkerResult stores success metadata."""
    result = WorkerResult(ok=True, data="ok")
    assert result.ok is True
    assert result.data == "ok"
