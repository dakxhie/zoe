"""Phase C tool catalog and registry (ZOE_PHASE_A1_DESIGN.md §8.1, §9, §24.2).

The catalog holds the ``ToolDefinition`` of every structured tool. It contains
only the accepted read-only tools, the authorized web tool and the explicit
memory tool:

=============  ===============  =========================================  ===========
tool           permission       implementation (reused)                    availability
=============  ===============  =========================================  ===========
list_files     filesystem.read  B1 ``tools.filesystem.list_files``         available
read_file      filesystem.read  B1 ``tools.filesystem.read_file_window``   available
find_file      filesystem.read  B1 ``tools.filesystem.find_file``          available
search_text    filesystem.read  B1 ``tools.filesystem.search_text``        available
calculate      compute          B3 ``tools.calculator.calculate``          available
get_time       clock            ``tools.datetime_tool``                    available
search_code    code.search      ``codebase.retriever.search_code``         available
web_search     network          B2 ``web.policy.gated_search``             available*
fetch_page     network          (B2 ``web.reader``; not exposed)           unavailable
remember       memory.write     ``memory_review.process_memory_candidate``  available**
=============  ===============  =========================================  ===========

``*`` available as a definition; every call still needs the turn-scoped B2
authorization from the current user message. ``fetch_page`` exists only as an
unavailable definition: the accepted contract lists it as future (§24.2).

``**`` (Phase E remediation) ``remember`` saves one fact through the existing
memory write path (``memory.store.save_memory``'s pipeline, with the
assistant-reply inference disabled). Every call needs the turn-scoped memory
authorization that only an explicit remember request in the current user
message produces (``tools.tool_loop``), is denied outside an active tool loop,
refuses secrets and facts not stated in the current message (PolicyGate).

There is no file write, delete, rename, shell, process, git-mutation or other
side-effect tool, and the registry refuses to register one: the only
side-effect class besides network is ``memory_write``, accepted for exactly
the tool named ``remember``. Handlers are thin
adapters over the existing B1/B2/B3 code (no second security system) and run
only inside the ``ToolExecutor`` (``require_executor``).
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Iterable

from plugins.tool_definition import (
    Availability,
    PermissionClass,
    SideEffect,
    ToolDefinition,
    ToolDefinitionError,
    TrustClass,
)
from tools.result_envelope import TOOL_LIMITS, ResultStatus, ToolLimits
from tools.tool_protocol import MEMORY_NOT_AUTHORIZED_MESSAGE, WEB_MESSAGES, ToolError, require_executor

logger = logging.getLogger(__name__)

# Name fragments that can never be registered as a Phase C tool.
FORBIDDEN_NAME_PARTS = (
    "write",
    "edit",
    "delete",
    "remove",
    "rename",
    "move",
    "copy",
    "mkdir",
    "shell",
    "exec",
    "run",
    "process",
    "command",
    "git",
    "commit",
    "push",
    "unsafe",
    "install",
    "remember",
    "save",
)

# The single exception to FORBIDDEN_NAME_PARTS (Phase E remediation): exactly
# this name, and only with the memory_write side effect / memory.write
# permission. ``remember_x``, ``save``, ``write_memory`` ... stay refused.
MEMORY_TOOL_NAME = "remember"
MAX_MEMORY_FACT_CHARS = 500
MEMORY_NOT_STORED = "memory_not_stored"

# B1 path arguments checked by the PolicyGate before execution: tool -> (argument, AccessMode).
FILESYSTEM_PATH_ARGUMENTS: dict[str, tuple[str, str]] = {
    "list_files": ("path", "list"),
    "read_file": ("path", "read"),
    "find_file": ("root", "list"),
    "search_text": ("root", "list"),
}

_PATH = {"type": "string", "minLength": 1, "maxLength": 512}


class ToolRegistry:
    """Lookup of structured tool definitions by name (or canonical ``zoe.<name>`` id)."""

    def __init__(self, definitions: Iterable[ToolDefinition] = ()) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: ToolDefinition) -> None:
        if not isinstance(definition, ToolDefinition):
            raise ToolDefinitionError("only ToolDefinition instances can be registered")
        memory_tool = (
            definition.name == MEMORY_TOOL_NAME
            and definition.side_effect is SideEffect.MEMORY_WRITE
            and definition.permission is PermissionClass.MEMORY_WRITE
        )
        parts = set(definition.name.split("_"))
        if not memory_tool and any(part in parts for part in FORBIDDEN_NAME_PARTS):
            raise ToolDefinitionError("side-effect tools cannot be registered in Phase C")
        if not memory_tool and definition.side_effect not in {SideEffect.NONE, SideEffect.NETWORK}:
            raise ToolDefinitionError("side-effect tools cannot be registered in Phase C")
        if definition.name in self._tools:
            raise ToolDefinitionError(f"duplicate tool name {definition.name!r}")
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition | None:
        if not isinstance(name, str):
            return None
        if name.startswith("zoe."):
            name = name[len("zoe.") :]
        return self._tools.get(name)

    def resolve_wire_name(self, wire_name: str) -> str:
        """Map a Qwen wire ``name`` to a tool name (unknown names pass through unchanged)."""
        definition = self.get(wire_name)
        return definition.name if definition is not None else wire_name

    def names(self) -> list[str]:
        return sorted(self._tools)

    def definitions(self) -> list[ToolDefinition]:
        return [self._tools[name] for name in self.names()]

    def available(self) -> list[ToolDefinition]:
        return [d for d in self.definitions() if d.available]

    def wire_schemas(self) -> list[dict[str, Any]]:
        """Function schemas for available tools only (the PolicyGate still decides)."""
        return [d.wire_schema() for d in self.available()]


# ---------------------------------------------------------------------------
# Handlers (thin adapters over B1 / B2 / B3 code)
# ---------------------------------------------------------------------------


def _list_files(path: str) -> dict[str, Any]:
    require_executor()
    from tools.filesystem import list_files

    return {"path": path, "content": list_files(path)}


def _read_file(path: str, start_line: int, max_lines: int) -> dict[str, Any]:
    require_executor()
    from tools.filesystem import read_file_window

    window = read_file_window(path, start_line=start_line, max_lines=max_lines)
    payload: dict[str, Any] = {
        "path": window.path,
        "content": "\n".join(window.lines),
        "start_line": window.start_line,
        "end_line": window.end_line,
        "total_lines": window.total_lines,
        "truncated": window.truncated,
        "redactions": window.redacted_lines,
    }
    if window.truncated:
        payload["next_start_line"] = window.end_line + 1
    return payload


def _find_file(filename: str, root: str) -> dict[str, Any]:
    require_executor()
    from tools.filesystem import find_file

    return {"filename": filename, "root": root, "content": find_file(filename, root)}


def _search_text(text: str, root: str) -> dict[str, Any]:
    require_executor()
    from tools.filesystem import search_text

    return {"text": text, "root": root, "content": search_text(text, root)}


def _calculate(expression: str) -> dict[str, Any]:
    require_executor()
    from tools.calculator import calculate

    return {"expression": expression, "result": calculate(expression)}


def _get_time(kind: str, location: str = "") -> dict[str, Any]:
    require_executor()
    from tools.datetime_tool import get_datetime_response

    if location:
        query = f"what time is it in {location}" if kind == "time" else f"what is the date in {location}"
    else:
        query = "current time" if kind == "time" else "current date"
    text = get_datetime_response(query)
    if text is None:
        raise ToolError("invalid_arguments", "I don't recognise that location's time zone.")
    return {"kind": kind, "text": text}


def _search_code(query: str, top_k: int) -> dict[str, Any]:
    require_executor()
    from codebase.retriever import search_code

    hits = search_code(query, top_k=top_k)
    return {
        "query": query,
        "results": [
            {
                "path": str(hit.get("path", "")),
                "filename": str(hit.get("filename", "")),
                "language": str(hit.get("language", "")),
                "content": str(hit.get("content", "")),
            }
            for hit in hits
        ],
    }


def _web_search(query: str, max_results: int) -> dict[str, Any]:
    """B2 gated search. The model's ``query`` never leaves the machine (B2 rule)."""
    require_executor()
    from web.policy import gated_search

    outcome = gated_search(query, max_results=max_results)
    if not outcome.succeeded:
        error = outcome.error_type
        if error is None:
            from tools.result_envelope import ErrorType

            error = ErrorType.NO_RESULTS
        status = outcome.status if outcome.status is not ResultStatus.SUCCESS else ResultStatus.ERROR
        raise ToolError(error.value, WEB_MESSAGES[error], status)
    return {
        "query": outcome.query or "",
        "retrieved_at": outcome.retrieved_at,
        "items": [
            {
                "rank": item.rank,
                "title": item.title,
                "url": item.url,
                "snippet": item.snippet,
                "source_domain": item.source_domain,
            }
            for item in outcome.items
        ],
    }


def _remember(fact: str) -> dict[str, Any]:
    """Save one explicitly requested fact through the existing memory pipeline.

    The PolicyGate already required the current user message's explicit
    remember request, a fact stated in that message and no secret; the turn
    authorization is re-checked here. ``assistant_text=""`` keeps the
    pipeline's reply inference off, so nothing from history, assistant replies
    or tool results is ever stored. Scoring, forget filter, reinforcement,
    consolidation, de-duplication and storage are the existing ones.
    """
    require_executor()
    from tools.tool_loop import memory_write_authorized

    if not memory_write_authorized():
        raise ToolError("permission_denied", MEMORY_NOT_AUTHORIZED_MESSAGE, ResultStatus.DENIED)
    from memory.intelligence.memory_review import process_memory_candidate

    try:
        stored = process_memory_candidate(fact, assistant_text="")
    except Exception as exc:  # store errors stay internal (typed, no exception text)
        from core.safe_errors import log_safe_exception

        log_safe_exception(logger, "Memory tool", exc)
        raise ToolError("internal_error", "The memory store is unavailable right now.") from None
    if not stored:
        raise ToolError(
            MEMORY_NOT_STORED,
            "Nothing was stored: the memory already exists, or it is not a personal fact "
            "in the user's own words (for example 'My favorite color is blue').",
        )
    return {"stored": True, "fact": fact}


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------


def _obj(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "properties": properties, "required": required}


_CONTENT_LIMITS = ToolLimits(text_field="content", truncatable=frozenset({"content"}))


def build_default_definitions() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="list_files",
            tool_version=1,
            description="List files under a directory inside Zoe's workspace (read-only).",
            arguments_schema=_obj({"path": {**_PATH, "default": "."}}, []),
            result_schema=_obj({"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
            permission=PermissionClass.FILESYSTEM_READ,
            trust=TrustClass.UNTRUSTED,
            availability=Availability.AVAILABLE,
            timeout_s=30,
            limits=_CONTENT_LIMITS,
            source_kind="file_listing",
            handler=_list_files,
        ),
        ToolDefinition(
            name="read_file",
            tool_version=1,
            description="Read lines of a UTF-8 text file inside Zoe's workspace (read-only, secrets redacted).",
            arguments_schema=_obj(
                {
                    "path": _PATH,
                    "start_line": {"type": "integer", "minimum": 1, "maximum": 1_000_000, "default": 1},
                    "max_lines": {"type": "integer", "minimum": 1, "maximum": 400, "default": 200},
                },
                ["path"],
            ),
            result_schema=_obj(
                {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "total_lines": {"type": "integer"},
                    "truncated": {"type": "boolean"},
                    "redactions": {"type": "integer"},
                    "next_start_line": {"type": "integer"},
                },
                ["path", "content", "start_line", "end_line", "total_lines", "truncated", "redactions"],
            ),
            permission=PermissionClass.FILESYSTEM_READ,
            trust=TrustClass.UNTRUSTED,
            availability=Availability.AVAILABLE,
            timeout_s=15,
            limits=_CONTENT_LIMITS,
            source_kind="file",
            handler=_read_file,
        ),
        ToolDefinition(
            name="find_file",
            tool_version=1,
            description="Find files by name inside Zoe's workspace (read-only).",
            arguments_schema=_obj(
                {"filename": {"type": "string", "minLength": 1, "maxLength": 256}, "root": {**_PATH, "default": "."}},
                ["filename"],
            ),
            result_schema=_obj(
                {"filename": {"type": "string"}, "root": {"type": "string"}, "content": {"type": "string"}},
                ["filename", "root", "content"],
            ),
            permission=PermissionClass.FILESYSTEM_READ,
            trust=TrustClass.UNTRUSTED,
            availability=Availability.AVAILABLE,
            timeout_s=30,
            limits=_CONTENT_LIMITS,
            source_kind="file_listing",
            handler=_find_file,
        ),
        ToolDefinition(
            name="search_text",
            tool_version=1,
            description="Search UTF-8 text files inside Zoe's workspace for a string (read-only, secrets redacted).",
            arguments_schema=_obj(
                {"text": {"type": "string", "minLength": 1, "maxLength": 256}, "root": {**_PATH, "default": "."}},
                ["text"],
            ),
            result_schema=_obj(
                {"text": {"type": "string"}, "root": {"type": "string"}, "content": {"type": "string"}},
                ["text", "root", "content"],
            ),
            permission=PermissionClass.FILESYSTEM_READ,
            trust=TrustClass.UNTRUSTED,
            availability=Availability.AVAILABLE,
            timeout_s=30,
            limits=_CONTENT_LIMITS,
            source_kind="file_search",
            handler=_search_text,
        ),
        ToolDefinition(
            name="calculate",
            tool_version=1,
            description="Evaluate arithmetic with + - * / % and parentheses (no exponents).",
            arguments_schema=_obj({"expression": {"type": "string", "minLength": 1, "maxLength": 256}}, ["expression"]),
            result_schema=_obj({"expression": {"type": "string"}, "result": {"type": "string"}}, ["expression", "result"]),
            permission=PermissionClass.COMPUTE,
            trust=TrustClass.UNTRUSTED,
            availability=Availability.AVAILABLE,
            timeout_s=5,
            limits=ToolLimits(truncatable=frozenset()),
            plugin_id="builtin.calculator",
            handler=_calculate,
        ),
        ToolDefinition(
            name="get_time",
            tool_version=1,
            description="Get the current local time or date, optionally for a city, country or IANA time zone.",
            arguments_schema=_obj(
                {
                    "kind": {"type": "string", "enum": ["time", "date"], "default": "time", "maxLength": 4},
                    "location": {
                        "type": "string",
                        "maxLength": 64,
                        "pattern": r"[A-Za-z][A-Za-z .'/_\-]{0,63}",
                    },
                },
                [],
            ),
            result_schema=_obj({"kind": {"type": "string"}, "text": {"type": "string"}}, ["kind", "text"]),
            permission=PermissionClass.CLOCK,
            trust=TrustClass.UNTRUSTED,
            availability=Availability.AVAILABLE,
            timeout_s=5,
            limits=ToolLimits(field_chars={"text": 256}, truncatable=frozenset({"text"})),
            plugin_id="builtin.datetime",
            handler=_get_time,
        ),
        ToolDefinition(
            name="search_code",
            tool_version=1,
            description="Semantic search over the indexed codebase (read-only; empty when nothing is indexed).",
            arguments_schema=_obj(
                {
                    "query": {"type": "string", "minLength": 1, "maxLength": 256},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 5, "default": 5},
                },
                ["query"],
            ),
            result_schema=_obj(
                {
                    "query": {"type": "string"},
                    "results": {
                        "type": "array",
                        "items": _obj(
                            {
                                "path": {"type": "string"},
                                "filename": {"type": "string"},
                                "language": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            ["path", "filename", "language", "content"],
                        ),
                    },
                },
                ["query", "results"],
            ),
            permission=PermissionClass.CODE_SEARCH,
            trust=TrustClass.UNTRUSTED,
            availability=Availability.AVAILABLE,
            timeout_s=90,
            limits=ToolLimits(max_items=5, field_chars={"content": 1200}, truncatable=frozenset({"content"})),
            plugin_id="builtin.code",
            source_kind="rag_document",
            handler=_search_code,
        ),
        ToolDefinition(
            name="web_search",
            tool_version=1,
            description=(
                "Search the web. Only works when the user's current message explicitly asks to search "
                "the web; the query sent is taken from that message."
            ),
            arguments_schema=_obj(
                {
                    "query": {"type": "string", "minLength": 1, "maxLength": 200},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 5, "default": 5},
                },
                ["query"],
            ),
            result_schema=_obj(
                {
                    "query": {"type": "string"},
                    "retrieved_at": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": _obj(
                            {
                                "rank": {"type": "integer"},
                                "title": {"type": "string"},
                                "url": {"type": "string"},
                                "snippet": {"type": "string"},
                                "source_domain": {"type": "string"},
                            },
                            ["rank", "title", "url", "snippet", "source_domain"],
                        ),
                    },
                },
                ["query", "retrieved_at", "items"],
            ),
            permission=PermissionClass.NETWORK,
            trust=TrustClass.UNTRUSTED_EXTERNAL,
            availability=Availability.AVAILABLE,
            side_effect=SideEffect.NETWORK,
            timeout_s=30,
            limits=TOOL_LIMITS["web_search"],
            plugin_id="builtin.web",
            source_kind="web",
            handler=_web_search,
        ),
        ToolDefinition(
            name="fetch_page",
            tool_version=1,
            description="Fetch the text of a page returned by this turn's web search (not available).",
            arguments_schema=_obj({"url": {"type": "string", "minLength": 1, "maxLength": 2048}}, ["url"]),
            result_schema=_obj(
                {
                    "url": {"type": "string"},
                    "title": {"type": "string"},
                    "retrieved_at": {"type": "string"},
                    "content": {"type": "string"},
                },
                ["url", "content"],
            ),
            permission=PermissionClass.NETWORK,
            trust=TrustClass.UNTRUSTED_EXTERNAL,
            availability=Availability.UNAVAILABLE,
            side_effect=SideEffect.NETWORK,
            timeout_s=30,
            limits=TOOL_LIMITS["fetch_page"],
            plugin_id="builtin.web",
            source_kind="web",
            handler=None,
        ),
        ToolDefinition(
            name=MEMORY_TOOL_NAME,
            tool_version=1,
            description=(
                "Save one fact about the user to long-term memory. Only when the current user message "
                "explicitly asks you to remember something; state the fact in the user's own words."
            ),
            arguments_schema=_obj(
                {"fact": {"type": "string", "minLength": 1, "maxLength": MAX_MEMORY_FACT_CHARS}}, ["fact"]
            ),
            result_schema=_obj({"stored": {"type": "boolean"}, "fact": {"type": "string"}}, ["stored", "fact"]),
            permission=PermissionClass.MEMORY_WRITE,
            trust=TrustClass.UNTRUSTED,
            availability=Availability.AVAILABLE,
            side_effect=SideEffect.MEMORY_WRITE,
            timeout_s=60,
            plugin_id="builtin.memory",
            source_kind="memory",
            handler=_remember,
        ),
    ]


_registry: ToolRegistry | None = None
_registry_lock = threading.Lock()


def get_tool_registry() -> ToolRegistry:
    """The process-wide structured tool registry."""
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = ToolRegistry(build_default_definitions())
        return _registry
