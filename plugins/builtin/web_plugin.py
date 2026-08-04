"""Web research routing builtin plugin."""

from __future__ import annotations

from core.text_utils import matches_any, normalize_text
from plugins.permissions import Permission
from plugins.plugin import Plugin, ToolCategory

WEB_PHRASES: tuple[str, ...] = (
    "latest",
    "today",
    "news",
    "current",
    "recent",
    "who is currently",
    "weather",
    "stock price",
    "exchange rate",
    "version",
    "release",
    "documentation",
    "official docs",
)


def _match(query: str) -> bool:
    return matches_any(normalize_text(query), WEB_PHRASES)


PLUGIN = Plugin(
    id="builtin.web",
    name="Web Research",
    version="1.0.0",
    author="Zoe AI",
    description="Route web search and live information queries",
    category=ToolCategory.RESEARCH,
    permissions=frozenset({Permission.INTERNET.value}),
    priority=70,
    route_id="web",
    examples=("Latest Python release", "Current weather in London"),
    match_query=_match,
)
