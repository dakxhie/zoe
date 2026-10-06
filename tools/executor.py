"""Tool execution layer for Zoe AI."""

from __future__ import annotations

import logging

from core.safe_errors import log_safe_exception
from tools.calculator import (
    CalculatorError,
    CalculatorInternalError,
    CalculatorMathError,
    calculate,
    is_calculator_request,
)
from tools.datetime_tool import get_datetime_response
from tools.filesystem import (
    FilesystemError,
    find_file,
    list_files,
    read_file,
    search_text,
)
from tools.router import route_query

logger = logging.getLogger(__name__)

FILESYSTEM_COMMANDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("list files", "show files"), "list"),
    (("read file", "open file"), "read"),
    (("find file",), "find"),
    (("search text", "search file"), "search"),
)


def _extract_argument(query: str, phrases: tuple[str, ...]) -> str:
    lowered = query.lower()
    for phrase in phrases:
        index = lowered.find(phrase)
        if index != -1:
            return query[index + len(phrase) :].strip().strip("\"'")
    return ""


def _execute_filesystem(query: str) -> tuple[bool, str]:
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
            if getattr(exc, "error_type", "") in {"sensitive_path", "sensitive_content"} and argument:
                # Phase B2 (A.1 §6.4): remember (as keyed fingerprints) that this
                # path was refused, so it cannot later leave in a web query.
                from tools.session_markers import record_sensitive_path

                record_sensitive_path(argument)
            return True, str(exc)

    return False, ""


def _try_plugin_execute(query: str, route: str) -> tuple[bool, str]:
    from plugins.manager import execute_plugin_route, initialize_plugins

    initialize_plugins()
    if route in {"chat", "vision", "filesystem"}:
        return False, ""
    return execute_plugin_route(query, route)


def execute_tool(query: str) -> tuple[bool, str]:
    """Execute a lightweight tool when the query is handled outside the LLM.

    Phase B3: nothing escapes this boundary. Typed tool errors keep their own
    safe messages; any unexpected exception ends the tool step with a fixed
    safe message (no traceback, no exception text).

    Phase D: legacy free-text execution; blocked while the tool loop owns
    execution (``ZOE_TOOL_LOOP`` ON or a loop active).
    """
    from tools.tool_loop import guard_legacy_execution

    guard_legacy_execution("tools.executor.execute_tool")
    try:
        return _execute_tool(query)
    except Exception as exc:
        safe = log_safe_exception(logger, "Tool execution", exc)
        return True, safe.message


def _execute_tool(query: str) -> tuple[bool, str]:
    tool = route_query(query)

    if tool == "filesystem":
        handled, result = _execute_filesystem(query)
        if handled:
            return True, result
        return False, ""

    handled, result = _try_plugin_execute(query, tool)
    if handled:
        return True, result

    if tool != "chat":
        return False, ""

    if is_calculator_request(query):
        try:
            return True, calculate(query)
        except (CalculatorMathError, CalculatorInternalError) as exc:
            # e.g. "5 / 0": typed math_error, the turn completes safely.
            return True, exc.safe_message
        except CalculatorError:
            return False, ""

    datetime_response = get_datetime_response(query)
    if datetime_response is not None:
        return True, datetime_response

    return False, ""
