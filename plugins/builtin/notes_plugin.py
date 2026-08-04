"""Notes routing builtin plugin."""

from __future__ import annotations

from core.text_utils import matches_any, normalize_text
from plugins.plugin import Plugin, ToolCategory
from plugins.permissions import Permission

NOTES_PHRASES: tuple[str, ...] = (
    "personal notes",
    "my notes",
    "about my notes",
    "notes",
    "profile",
)


def _match(query: str) -> bool:
    return matches_any(normalize_text(query), NOTES_PHRASES)


PLUGIN = Plugin(
    id="builtin.notes",
    name="Personal Notes",
    version="1.0.0",
    author="Zoe AI",
    description="Route personal notes retrieval queries",
    category=ToolCategory.PRODUCTIVITY,
    permissions=frozenset({Permission.MEMORY.value}),
    priority=88,
    route_id="notes",
    examples=("Search my notes", "What do my notes say about Python?"),
    match_query=_match,
)
