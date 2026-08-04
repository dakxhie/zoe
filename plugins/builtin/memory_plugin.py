"""Memory routing builtin plugin."""

from __future__ import annotations

from core.text_utils import matches_any, normalize_text
from plugins.permissions import Permission
from plugins.plugin import Plugin, ToolCategory

MEMORY_PHRASES: tuple[str, ...] = (
    "my favorite",
    "my name",
    "where do i live",
    "what is my goal",
    "remember",
    "what do you know about me",
)


def _match(query: str) -> bool:
    return matches_any(normalize_text(query), MEMORY_PHRASES)


PLUGIN = Plugin(
    id="builtin.memory",
    name="Memory",
    version="1.0.0",
    author="Zoe AI",
    description="Route personal memory retrieval queries",
    category=ToolCategory.MEMORY,
    permissions=frozenset({Permission.MEMORY.value}),
    priority=90,
    route_id="memory",
    examples=("What is my favorite color?", "What do you know about me?"),
    match_query=_match,
)
