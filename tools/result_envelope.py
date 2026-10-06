"""Universal tool-result envelope and bounding layer (ZOE_PHASE_A1_DESIGN.md §8.3, §23, §24).

This is the single authoritative bounding mechanism for tool results. Phase B2
routes web results (``web_search`` and page fetches, ``fetch_page``) through it;
the Phase C ToolExecutor (``tools.tool_protocol``) calls the same
``bound_result`` for every tool.

Order (§24.1): tool-specific limits -> depth -> keys -> items -> strings ->
serialized bytes -> tokens. Truncation keeps ``status: success`` and sets
``truncated: true`` plus a ``truncation`` record (§24.3). If no valid bounded
shape exists, the result is ``status: error`` with
``error.type: result_unrepresentable`` (§24.4).

Token counting (§23.2 R1) uses the already-loaded model tokenizer when one is
in memory; this module never loads a model. Without a loaded tokenizer it uses
a conservative estimate (one token per 3 UTF-8 bytes, which over-counts for
ordinary text) so limits are never under-enforced.
"""

from __future__ import annotations

import copy
import json
import math
import sys
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from tools.secret_scan import REDACTED_LINE

PROTOCOL = "zoe.tool/1"


class ResultStatus(str, Enum):
    """Universal tool-result status (§8.3 amended by §24.4)."""

    SUCCESS = "success"
    ERROR = "error"
    DENIED = "denied"
    TIMEOUT = "timeout"
    BUDGET_EXCEEDED = "budget_exceeded"
    CANCELLED = "cancelled"


class ErrorType(str, Enum):
    """The eight canonical ``error.type`` values (§8.4, §6.5, §24.4).

    This is the only public error vocabulary. Finer distinctions (offline mode,
    no buildable query, missing provider package, ...) are internal diagnostic
    codes on the producing objects, never error types.
    """

    WEB_NOT_AUTHORIZED = "web_not_authorized"
    EGRESS_BLOCKED_SENSITIVE = "egress_blocked_sensitive"
    NETWORK_UNAVAILABLE = "network_unavailable"
    NO_RESULTS = "no_results"
    TIMEOUT = "timeout"
    BUDGET_EXCEEDED = "budget_exceeded"
    FETCH_FAILED = "fetch_failed"
    RESULT_UNREPRESENTABLE = "result_unrepresentable"


CANONICAL_ERROR_TYPES: frozenset[str] = frozenset(e.value for e in ErrorType)


@dataclass(frozen=True)
class GlobalLimits:
    """Executor-enforced global limits, the final safety boundary (§24.1)."""

    max_bytes: int = 16 * 1024
    max_tokens: int = 1_000
    max_items: int = 50
    max_depth: int = 6
    max_string: int = 8 * 1024
    max_keys: int = 64


GLOBAL_LIMITS = GlobalLimits()
# Largest ``source`` echoed back in a result_unrepresentable error envelope.
MAX_ERROR_SOURCE_BYTES = 1024


@dataclass(frozen=True)
class ToolLimits:
    """Stricter per-tool limits (§24.2). They can never loosen the global ones."""

    max_items: int | None = None
    field_chars: dict[str, int] = field(default_factory=dict)
    text_field: str | None = None
    max_text_bytes: int | None = None
    # String fields that may be shortened to fit. ``None`` means every string.
    truncatable: frozenset[str] | None = None


TOOL_LIMITS: dict[str, ToolLimits] = {
    "web_search": ToolLimits(
        max_items=5,
        field_chars={"title": 200, "snippet": 300},
        truncatable=frozenset({"title", "snippet"}),
    ),
    "fetch_page": ToolLimits(
        text_field="content",
        max_text_bytes=8 * 1024,
        truncatable=frozenset({"content", "title"}),
    ),
}

# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

_token_counter: Callable[[str], int] | None = None


def set_token_counter(counter: Callable[[str], int] | None) -> None:
    """Override token counting (tests, or a caller holding a tokenizer)."""
    global _token_counter
    _token_counter = counter


def estimate_tokens(text: str) -> int:
    """Conservative token estimate: one token per 3 UTF-8 bytes."""
    return math.ceil(len(text.encode("utf-8")) / 3)


def count_tokens(text: str) -> int:
    """Count tokens with an override, else a loaded tokenizer, else the estimate."""
    if _token_counter is not None:
        return int(_token_counter(text))
    generation = sys.modules.get("brain.generation")
    loaded = getattr(generation, "tokenizer", None) if generation is not None else None
    if loaded is not None:
        try:
            return len(loaded.encode(text, add_special_tokens=False))
        except Exception:  # never let counting break bounding
            pass
    return estimate_tokens(text)


# ---------------------------------------------------------------------------
# Envelope construction
# ---------------------------------------------------------------------------


def _serialize(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, sort_keys=False, separators=(",", ":"))


def _byte_len(text: str) -> int:
    return len(text.encode("utf-8"))


def make_envelope(
    tool: str,
    status: ResultStatus,
    *,
    result: Any = None,
    error_type: ErrorType | None = None,
    message: str = "",
    trust: str = "untrusted",
    source: dict[str, Any] | None = None,
    call_id: str | None = None,
    truncated: bool = False,
    truncation: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a §8.3 tool_result envelope."""
    error = None
    if error_type is not None:
        error = {"type": error_type.value, "message": message, "retryable": False}
    return {
        "type": "tool_result",
        "protocol": PROTOCOL,
        "call_id": call_id or f"call_{uuid.uuid4().hex[:10]}",
        "tool": tool,
        "status": status.value,
        "trust": trust,
        "source": source or {},
        "result": result if status is ResultStatus.SUCCESS else None,
        "truncated": bool(truncated),
        "truncation": truncation,
        "error": error,
        "metadata": metadata or {},
    }


def error_envelope(
    tool: str,
    status: ResultStatus,
    error_type: ErrorType,
    message: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Envelope for denied/error/timeout/budget_exceeded results (no payload)."""
    return make_envelope(tool, status, error_type=error_type, message=message, **kwargs)


# ---------------------------------------------------------------------------
# Deterministic, boundary-aware text truncation (§23.4)
# ---------------------------------------------------------------------------


def safe_cut(text: str, max_chars: int) -> str:
    """Cut ``text`` to at most ``max_chars`` characters, deterministically.

    Prefers a line boundary, then whitespace, in the last half of the window;
    works on code points (UTF-8 safe) and never splits a redaction marker.
    """
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    cut = max_chars
    window = text[:cut]
    floor = cut // 2
    newline = window.rfind("\n")
    if newline >= floor:
        cut = newline
    else:
        space = max(window.rfind(" "), window.rfind("\t"))
        if space >= floor:
            cut = space
    marker_start = text.rfind(REDACTED_LINE[:10], 0, cut)
    if marker_start != -1 and marker_start + len(REDACTED_LINE) > cut:
        cut = marker_start
    return text[:cut].rstrip()


def _cut_to_bytes(text: str, max_bytes: int) -> str:
    if _byte_len(text) <= max_bytes:
        return text
    encoded = text.encode("utf-8")[:max_bytes]
    decoded = encoded.decode("utf-8", errors="ignore")
    return safe_cut(text, len(decoded))


# ---------------------------------------------------------------------------
# Generic bounding
# ---------------------------------------------------------------------------


class _Unrepresentable(Exception):
    pass


def _depth(obj: Any, level: int = 1) -> int:
    if isinstance(obj, dict):
        return max([level, *(_depth(v, level + 1) for v in obj.values())])
    if isinstance(obj, list):
        return max([level, *(_depth(v, level + 1) for v in obj)])
    return level


def _max_keys(obj: Any) -> int:
    if isinstance(obj, dict):
        return max([len(obj), *(_max_keys(v) for v in obj.values())])
    if isinstance(obj, list):
        return max([0, *(_max_keys(v) for v in obj)])
    return 0


def _string_slots(obj: Any, truncatable: frozenset[str] | None, path: tuple = ()) -> list[tuple]:
    """Paths of string fields that may be shortened."""
    slots: list[tuple] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str):
                if truncatable is None or key in truncatable:
                    slots.append((*path, key))
            else:
                slots.extend(_string_slots(value, truncatable, (*path, key)))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            if isinstance(value, str):
                if truncatable is None:
                    slots.append((*path, index))
            else:
                slots.extend(_string_slots(value, truncatable, (*path, index)))
    return slots


def _get(obj: Any, path: tuple) -> Any:
    for part in path:
        obj = obj[part]
    return obj


def _set(obj: Any, path: tuple, value: Any) -> None:
    for part in path[:-1]:
        obj = obj[part]
    obj[path[-1]] = value


def _truncate_lists(obj: Any, limit: int) -> tuple[int, int]:
    """Cap every list at ``limit``; return (largest original, returned) counts."""
    original = returned = 0
    if isinstance(obj, dict):
        for value in obj.values():
            o, r = _truncate_lists(value, limit)
            if o > original:
                original, returned = o, r
    elif isinstance(obj, list):
        if len(obj) > limit:
            original, returned = len(obj), limit
            del obj[limit:]
        for value in obj:
            o, r = _truncate_lists(value, limit)
            if o > original:
                original, returned = o, r
    return original, returned


def bound_result(
    tool: str,
    result: Any,
    *,
    trust: str = "untrusted",
    source: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    limits: GlobalLimits = GLOBAL_LIMITS,
    tool_limits: ToolLimits | None = None,
    call_id: str | None = None,
) -> dict[str, Any]:
    """Bound a successful tool payload and return its envelope.

    Never raises for oversized or malformed payloads: those become a
    ``result_unrepresentable`` error envelope. ``tool_limits`` (Phase C: the
    tool definition's own limits) replaces the ``TOOL_LIMITS`` entry; it can
    only tighten, never loosen, the global ``limits``. ``call_id`` (Phase C:
    the orchestrator-generated ``ToolCall.id``) is echoed in the envelope.
    """
    if tool_limits is None:
        tool_limits = TOOL_LIMITS.get(tool, ToolLimits())
    base_meta = dict(metadata or {})

    def _unrepresentable(reason: str) -> dict[str, Any]:
        # The error envelope must itself stay small: drop an oversized source
        # (e.g. a huge URL) rather than echo it back into context.
        safe_source = source
        try:
            if source is not None and _byte_len(_serialize(source)) > MAX_ERROR_SOURCE_BYTES:
                safe_source = {"kind": source.get("kind"), "omitted": "oversized"}
        except (TypeError, ValueError):
            safe_source = None
        return error_envelope(
            tool,
            ResultStatus.ERROR,
            ErrorType.RESULT_UNREPRESENTABLE,
            "The result could not be represented within Zoe's result limits.",
            trust=trust,
            source=safe_source,
            call_id=call_id,
            metadata={**base_meta, "unrepresentable_reason": reason},
        )

    try:
        original_serialized = _serialize(result)
        payload = copy.deepcopy(result)
    except (TypeError, ValueError, RecursionError):
        return _unrepresentable("not_serializable")

    original_bytes = _byte_len(original_serialized)
    reasons: list[str] = []
    detail: dict[str, Any] = {}

    # 1. Tool-specific limits (always at least as strict as the global ones).
    if tool_limits.max_items is not None and isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, list) and len(value) > tool_limits.max_items:
                detail.setdefault("original_items", len(value))
                detail["returned_items"] = tool_limits.max_items
                del value[tool_limits.max_items :]
                reasons.append("tool_limit")
    if tool_limits.field_chars:
        for slot in _string_slots(payload, frozenset(tool_limits.field_chars)):
            limit = tool_limits.field_chars[slot[-1]]
            value = _get(payload, slot)
            if len(value) > limit:
                _set(payload, slot, safe_cut(value, limit))
                reasons.append("tool_limit")
    text_field = tool_limits.text_field
    if text_field and isinstance(payload, dict) and isinstance(payload.get(text_field), str):
        text = payload[text_field]
        detail["original_chars"] = len(text)
        if tool_limits.max_text_bytes is not None and _byte_len(text) > tool_limits.max_text_bytes:
            payload[text_field] = _cut_to_bytes(text, tool_limits.max_text_bytes)
            reasons.append("tool_limit")

    # 2. Depth and keys: reducing these would break the output shape.
    if _depth(payload) > limits.max_depth:
        return _unrepresentable("max_depth")
    if _max_keys(payload) > limits.max_keys:
        return _unrepresentable("max_keys")

    # 3. Items.
    original_items, returned_items = _truncate_lists(payload, limits.max_items)
    if original_items:
        detail.setdefault("original_items", original_items)
        detail["returned_items"] = returned_items
        reasons.append("max_items")

    # 4. Strings.
    for slot in _string_slots(payload, None):
        value = _get(payload, slot)
        if _byte_len(value) > limits.max_string:
            if tool_limits.truncatable is not None and slot[-1] not in tool_limits.truncatable:
                return _unrepresentable("max_string")
            _set(payload, slot, _cut_to_bytes(value, limits.max_string))
            reasons.append("max_string")

    # 5/6. Serialized bytes, then tokens, measured over the whole envelope
    # (including fixed-width size metadata so the final envelope still fits).
    def _build(current: Any, truncated: bool, sizes: tuple[int, int] = (99_999, 99_999)) -> dict[str, Any]:
        truncation = None
        if truncated:
            truncation = {"reason": reasons[0] if reasons else "max_bytes", "reasons": list(dict.fromkeys(reasons))}
            truncation.update(detail)
            truncation["original_bytes"] = original_bytes
            if text_field and isinstance(current, dict) and isinstance(current.get(text_field), str):
                truncation["returned_chars"] = len(current[text_field])
            truncation["returned_bytes"] = sizes[0]
        return make_envelope(
            tool,
            ResultStatus.SUCCESS,
            result=current,
            trust=trust,
            source=source,
            truncated=truncated,
            truncation=truncation,
            call_id=call_id,
            metadata={**base_meta, "bytes": sizes[0], "tokens": sizes[1]},
        )

    def _measure(env: dict[str, Any]) -> tuple[int, int]:
        serialized = _serialize(env)
        return _byte_len(serialized), count_tokens(serialized)

    def _fits(env: dict[str, Any]) -> bool:
        size, tokens = _measure(env)
        return size <= limits.max_bytes and tokens <= limits.max_tokens

    size, tokens = _measure(_build(payload, True))
    if size > limits.max_bytes:
        reasons.append("max_bytes")
    if tokens > limits.max_tokens:
        reasons.append("max_tokens")

    slots = _string_slots(payload, tool_limits.truncatable)
    while not _fits(_build(payload, True)):
        live = [s for s in slots if _get(payload, s)]
        if not live:
            return _unrepresentable("fixed_fields_exceed_limits")
        slot = max(live, key=lambda s: (len(_get(payload, s)), str(s)))
        value = _get(payload, slot)
        low, high, best = 0, len(value), 0
        while low <= high:
            mid = (low + high) // 2
            _set(payload, slot, safe_cut(value, mid))
            if _fits(_build(payload, True)):
                best, low = mid, mid + 1
            else:
                high = mid - 1
        _set(payload, slot, safe_cut(value, best))

    truncated = bool(reasons)
    envelope = _build(payload, truncated)
    final_sizes = _measure(envelope)
    envelope = _build(payload, truncated, final_sizes)
    if not _fits(envelope):
        return _unrepresentable("metadata_exceeds_limits")
    return envelope
