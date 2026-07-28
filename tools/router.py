"""Rule-based routing for Zoe AI tool selection."""

from __future__ import annotations

import re

from core.text_utils import matches_any, normalize_text

MEMORY_PHRASES: tuple[str, ...] = (
    "my favorite",
    "my name",
    "where do i live",
    "what is my goal",
    "remember",
    "what do you know about me",
)

NOTES_PHRASES: tuple[str, ...] = (
    "personal notes",
    "my notes",
    "about my notes",
    "notes",
    "profile",
)

PDF_PHRASES: tuple[str, ...] = (
    "pdf",
    "document",
    "chapter",
    "uploaded book",
    "uploaded file",
)

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


def _is_code_query(text: str) -> bool:
    """Return True when the query looks like a code search request."""
    if _contains_image_path(text):
        return False
    if matches_any(text, CODE_PHRASES):
        return True
    return "()" in text


def _contains_image_path(text: str) -> bool:
    """Return True when the query references a supported image file."""
    return extract_image_path(text) is not None


def extract_image_path(query: str) -> str | None:
    """Extract the first supported image file path from a query."""
    normalized = query.replace("\\", "/")
    tokens = re.findall(r"\S+", normalized)

    for token in tokens:
        cleaned = token.strip("\"'`,()[]{}")
        lowered = cleaned.lower()
        if any(lowered.endswith(extension) for extension in IMAGE_EXTENSIONS):
            return cleaned

    return None


def _is_vision_query(text: str) -> bool:
    """Return True when the query asks for image understanding."""
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
    """Classify a user query into one of Zoe's available tool routes."""
    normalized = normalize_text(query)

    if not normalized:
        return "chat"

    if matches_any(normalized, MEMORY_PHRASES):
        return "memory"

    if matches_any(normalized, NOTES_PHRASES):
        return "notes"

    if _is_vision_query(normalized):
        return "vision"

    if matches_any(normalized, PDF_PHRASES):
        return "pdf"

    if matches_any(normalized, FILESYSTEM_PHRASES):
        return "filesystem"

    if _is_code_query(normalized):
        return "code"

    if matches_any(normalized, WEB_PHRASES):
        return "web"

    return "chat"
