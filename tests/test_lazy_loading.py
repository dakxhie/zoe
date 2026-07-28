"""Pytest coverage for lazy model loading."""

from __future__ import annotations

from unittest.mock import patch


def test_cli_doctor_does_not_load_model() -> None:
    """Doctor health checks should not load the LLM."""
    with patch("core.doctor.run_doctor", return_value=object()), patch(
        "core.doctor.print_doctor_report"
    ), patch("brain.generation.load_model") as load_model:
        from cli.main import doctor

        doctor()

    load_model.assert_not_called()


def test_datetime_tool_does_not_load_model() -> None:
    """Datetime responses should not load the LLM."""
    from tools.datetime_tool import get_datetime_response

    with patch("brain.generation.load_model") as load_model:
        assert get_datetime_response("Current time")
        assert get_datetime_response("What time is it in India?")

    load_model.assert_not_called()


def test_calculator_does_not_load_model() -> None:
    """Calculator responses should not load the LLM."""
    from tools.calculator import calculate

    with patch("brain.generation.load_model") as load_model:
        assert calculate("2+2") == "4"

    load_model.assert_not_called()
