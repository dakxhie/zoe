"""Rule-based routing for Zoe AI tool selection."""

from __future__ import annotations

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

FILESYSTEM_PHRASES: tuple[str, ...] = (
    "list files",
    "show files",
    "open file",
    "read file",
    "find file",
    "search file",
    "search text",
)

VALID_ROUTES: frozenset[str] = frozenset(
    {"chat", "memory", "notes", "pdf", "code", "filesystem"}
)


def _normalize(query: str) -> str:
    """Normalize user input for case-insensitive matching."""
    return " ".join(query.strip().lower().split())


def _matches_any(text: str, phrases: tuple[str, ...]) -> bool:
    """Return True when any phrase appears in the text."""
    return any(phrase in text for phrase in phrases)


def _is_code_query(text: str) -> bool:
    """Return True when the query looks like a code search request."""
    if _matches_any(text, CODE_PHRASES):
        return True
    return "()" in text


def route_query(query: str) -> str:
    """Classify a user query into one of Zoe's available tool routes."""
    normalized = _normalize(query)

    if not normalized:
        return "chat"

    if _matches_any(normalized, MEMORY_PHRASES):
        return "memory"

    if _matches_any(normalized, NOTES_PHRASES):
        return "notes"

    if _matches_any(normalized, PDF_PHRASES):
        return "pdf"

    if _matches_any(normalized, FILESYSTEM_PHRASES):
        return "filesystem"

    if _is_code_query(normalized):
        return "code"

    return "chat"
