"""Code search routing builtin plugin."""

from __future__ import annotations

import re

from core.text_utils import matches_any, normalize_text
from plugins.plugin import Plugin, ToolCategory
from tools.router import extract_image_path

CODE_PHRASES: tuple[str, ...] = (
    "code",
    "function",
    "class",
    "python file",
    "javascript",
    "bug",
    "repository",
    "project source",
)


def _match(query: str) -> bool:
    text = normalize_text(query)
    if extract_image_path(query):
        return False
    if matches_any(text, CODE_PHRASES):
        return True
    return "()" in query


PLUGIN = Plugin(
    id="builtin.code",
    name="Code Index",
    version="1.0.0",
    author="Zoe AI",
    description="Route indexed repository code queries",
    category=ToolCategory.CODING,
    permissions=frozenset(),
    priority=80,
    route_id="code",
    examples=("Where is generate_response implemented?", "Find bug in pipeline"),
    match_query=_match,
)
