"""Tool execution layer for Zoe AI."""

from __future__ import annotations

from tools.calculator import CalculatorError, calculate, is_calculator_request
from tools.datetime_tool import get_datetime_response
from tools.filesystem import (
    FilesystemError,
    find_file,
    list_files,
    read_file,
    search_text,
)
from tools.router import route_query

FILESYSTEM_COMMANDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("list files", "show files"), "list"),
    (("read file", "open file"), "read"),
    (("find file",), "find"),
    (("search text", "search file"), "search"),
)


def _extract_argument(query: str, phrases: tuple[str, ...]) -> str:
    """Return the text following a matched filesystem command phrase."""
    lowered = query.lower()
    for phrase in phrases:
        index = lowered.find(phrase)
        if index != -1:
            return query[index + len(phrase) :].strip().strip("\"'")
    return ""


def _execute_filesystem(query: str) -> tuple[bool, str]:
    """Execute a read-only filesystem tool request."""
    normalized = query.lower()

    for phrases, command in FILESYSTEM_COMMANDS:
        if not any(phrase in normalized for phrase in phrases):
            continue

        argument = _extract_argument(query, phrases)

        try:
            if command == "list":
                return True, list_files(argument or ".")
            if command == "read":
                if not argument:
                    raise FilesystemError("A file path is required")
                return True, read_file(argument)
            if command == "find":
                if not argument:
                    raise FilesystemError("A filename is required")
                return True, find_file(argument)
            if command == "search":
                if not argument:
                    raise FilesystemError("Search text is required")
                return True, search_text(argument)
        except FilesystemError as exc:
            return True, str(exc)

    return False, ""


def execute_tool(query: str) -> tuple[bool, str]:
    """Execute a lightweight tool when the query is handled outside the LLM."""
    tool = route_query(query)

    if tool == "filesystem":
        handled, result = _execute_filesystem(query)
        if handled:
            return True, result
        return False, ""

    if tool != "chat":
        return False, ""

    if is_calculator_request(query):
        try:
            return True, calculate(query)
        except CalculatorError:
            return False, ""

    datetime_response = get_datetime_response(query)
    if datetime_response is not None:
        return True, datetime_response

    return False, ""
