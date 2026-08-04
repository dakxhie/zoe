"""Rule-based routing for Zoe AI tool selection."""

from __future__ import annotations

import logging
import re

from core.text_utils import matches_any, normalize_text

logger = logging.getLogger(__name__)

NOTES_PHRASES: tuple[str, ...] = (
    "personal notes",
    "my notes",
    "about my notes",
    "notes",
    "profile",
)

PDF_PHRASES: tuple[str, ...] = ()  # Routed via builtin.pdf plugin

FILESYSTEM_PHRASES: tuple[str, ...] = (
    "list files",
    "show files",
    "open file",
    "read file",
    "find file",
    "search file",
    "search text",
)

VISION_PHRASES: tuple[str, ...] = (
    "describe image",
    "read image",
    "what is in",
    "explain screenshot",
    "analyze image",
    "ocr",
    "photo",
    "picture",
    "graph",
    "chart",
    "receipt",
    "invoice",
    "scan",
    "document image",
)

IMAGE_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def _legacy_route_query(query: str) -> str:
    """Fallback routes for vision and filesystem (non-plugin routes)."""
    normalized = normalize_text(query)

    if not normalized:
        return "chat"

    if _is_vision_query(normalized):
        return "vision"

    if matches_any(normalized, FILESYSTEM_PHRASES):
        return "filesystem"

    return "chat"


def _plugin_route(query: str) -> str:
    from plugins.manager import initialize_plugins, route_query as plugin_route

    initialize_plugins()
    return plugin_route(query)


def _contains_image_path(text: str) -> bool:
    return extract_image_path(text) is not None


def extract_image_path(query: str) -> str | None:
    normalized = query.replace("\\", "/")
    tokens = re.findall(r"\S+", normalized)

    for token in tokens:
        cleaned = token.strip("\"'`,()[]{}")
        lowered = cleaned.lower()
        if any(lowered.endswith(extension) for extension in IMAGE_EXTENSIONS):
            return cleaned

    return None


def _is_vision_query(text: str) -> bool:
    if matches_any(text, VISION_PHRASES):
        return True
    return _contains_image_path(text) and matches_any(
        text,
        (
            "describe",
            "explain",
            "read",
            "summarize",
            "analyze",
            "what",
            "show",
            "error",
            "screenshot",
            "image",
        ),
    )


def route_query(query: str) -> str:
    """Classify a user query using the plugin registry with legacy fallback."""
    route = _plugin_route(query)
    if route != "chat":
        return route
    return _legacy_route_query(query)
