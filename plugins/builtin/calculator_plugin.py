"""Calculator builtin plugin."""

from __future__ import annotations

from plugins.permissions import Permission
from plugins.plugin import Plugin, ToolCategory
from plugins.sandbox import wrap_execute
from tools.calculator import CalculatorError, calculate, is_calculator_request


def _match(query: str) -> bool:
    return is_calculator_request(query)


def _execute(query: str) -> tuple[bool, str]:
    try:
        return True, calculate(query)
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
