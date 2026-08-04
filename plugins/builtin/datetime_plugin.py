"""Datetime builtin plugin."""

from __future__ import annotations

from plugins.plugin import Plugin, ToolCategory
from plugins.sandbox import wrap_execute
from tools.datetime_tool import get_datetime_response, is_datetime_request


def _match(query: str) -> bool:
    return is_datetime_request(query)


def _execute(query: str) -> tuple[bool, str]:
    response = get_datetime_response(query)
    if response is None:
        return False, ""
    return True, response


PLUGIN = Plugin(
    id="builtin.datetime",
    name="Date and Time",
    version="1.0.0",
    author="Zoe AI",
    description="Local date and time responses",
    category=ToolCategory.UTILITIES,
    permissions=frozenset(),
    priority=95,
    route_id="datetime",
    examples=("What time is it?", "Today's date"),
    match_query=_match,
    execute_query=wrap_execute("builtin.datetime", frozenset(), _execute),
)
