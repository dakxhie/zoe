"""Calculator builtin plugin."""

from __future__ import annotations

from plugins.permissions import Permission
from plugins.plugin import Plugin, ToolCategory
from plugins.sandbox import wrap_execute
from tools.calculator import (
    CalculatorError,
    CalculatorInternalError,
    CalculatorMathError,
    calculate,
    is_calculator_request,
)


def _match(query: str) -> bool:
    # Pure detection (Phase B3): parses and validates, never evaluates.
    return is_calculator_request(query)


def _execute(query: str) -> tuple[bool, str]:
    try:
        return True, calculate(query)
    except (CalculatorMathError, CalculatorInternalError) as exc:
        # Phase B3: a typed math_error / internal_error completes the turn
        # with its safe message (e.g. "5 / 0") instead of falling through.
        return True, exc.safe_message
    except CalculatorError:
        return False, ""


PLUGIN = Plugin(
    id="builtin.calculator",
    name="Calculator",
    version="1.0.0",
    author="Zoe AI",
    description="Safe arithmetic evaluation",
    category=ToolCategory.UTILITIES,
    permissions=frozenset(),
    priority=100,
    route_id="calculator",
    examples=("2+2", "10*(5+2)"),
    match_query=_match,
    execute_query=wrap_execute("builtin.calculator", frozenset(), _execute),
)
