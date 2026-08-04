"""PDF routing builtin plugin."""

from __future__ import annotations

from core.text_utils import matches_any, normalize_text
from plugins.plugin import Plugin, ToolCategory

PDF_PHRASES: tuple[str, ...] = (
    "pdf",
    "document",
    "chapter",
    "uploaded book",
    "uploaded file",
)


def _match(query: str) -> bool:
    return matches_any(normalize_text(query), PDF_PHRASES)


PLUGIN = Plugin(
    id="builtin.pdf",
    name="PDF Documents",
    version="1.0.0",
    author="Zoe AI",
    description="Route indexed PDF document queries",
    category=ToolCategory.RESEARCH,
    permissions=frozenset(),
    priority=75,
    route_id="pdf",
    examples=("Search my PDF for introduction", "Chapter 3 summary"),
    match_query=_match,
)
