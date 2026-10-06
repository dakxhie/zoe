"""Phase C tool definitions (ZOE_PHASE_A1_DESIGN.md §8.1, §9.1, §9.2, §9.4, §24.2).

A ``ToolDefinition`` is the registry entry for one structured tool: a frozen,
validated description of what the tool is called, which closed argument schema
it accepts, what it returns, which permission and trust class it has, whether
it is available, its stricter per-tool result limits (reusing
``tools.result_envelope.ToolLimits``) and its timeout.

Validation is strict and fails at construction time:

- ``name`` is ``snake_case``; the canonical id is ``zoe.<name>``.
- ``tool_version`` is a positive major version (§9.4).
- The argument schema is CLOSED (``additionalProperties: false`` on every
  object) and BOUNDED (every string has ``maxLength``, every integer has
  ``minimum`` and ``maximum``, every array has ``maxItems``). Only a small,
  explicit JSON-Schema subset is accepted; anything else (``$ref``,
  ``oneOf``, ``patternProperties``, unknown keywords, open objects) is
  rejected as unsafe.
- The result schema must be closed and typed (sizes are bounded afterwards by
  the executor's universal result limits, §24.1).
- Only read-only (``side_effect: none``) and network-read
  (``side_effect: network``) tools can be defined. Write, delete, rename,
  shell, process and git-mutation classes do not exist in Phase C (§14, §26.1).
- Every tool has a timeout with ``0 < timeout_s <= 120``.

Schemas are deep-frozen (mappings become read-only, lists become tuples) so a
definition cannot be mutated after validation.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping

from tools.result_envelope import ToolLimits

TOOL_ID_PREFIX = "zoe."
MAX_TIMEOUT_S = 120.0
MAX_DESCRIPTION_CHARS = 512

# Argument-schema bounds (the schema itself must stay small and bounded).
MAX_SCHEMA_DEPTH = 4
MAX_PROPERTIES = 16
MAX_ARG_STRING_CHARS = 4096
MAX_ARG_ARRAY_ITEMS = 50
MAX_ARG_INT_ABS = 10**9
MAX_PATTERN_CHARS = 256
MAX_ENUM_VALUES = 32

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,47}$")
_PROPERTY_RE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
_PLUGIN_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")

_COMMON_KEYWORDS = frozenset({"type", "description", "default", "enum"})
_KEYWORDS_BY_TYPE: dict[str, frozenset[str]] = {
    "object": frozenset({"properties", "required", "additionalProperties"}),
    "string": frozenset({"minLength", "maxLength", "pattern"}),
    "integer": frozenset({"minimum", "maximum"}),
    "number": frozenset({"minimum", "maximum"}),
    "boolean": frozenset(),
    "array": frozenset({"items", "maxItems", "minItems"}),
    "null": frozenset(),
}


class ToolDefinitionError(ValueError):
    """Raised when a tool definition or schema is unsafe or invalid."""


class PermissionClass(str, Enum):
    """What a tool may touch (§9.2). There is deliberately no write/process class."""

    FILESYSTEM_READ = "filesystem.read"
    COMPUTE = "compute"
    CLOCK = "clock"
    CODE_SEARCH = "code.search"
    NETWORK = "network"


class TrustClass(str, Enum):
    """Trust of the tool's *output* (§7.1). Tool output is never an instruction."""

    UNTRUSTED = "untrusted"
    UNTRUSTED_EXTERNAL = "untrusted_external"


class SideEffect(str, Enum):
    """Allowed side-effect classes in Phase C (§8.1): read-only and network-read only."""

    NONE = "none"
    NETWORK = "network"


class Availability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


# Permission classes that may never be combined with a non-network side effect.
_NETWORK_PERMISSIONS = frozenset({PermissionClass.NETWORK})


# ---------------------------------------------------------------------------
# Deep freezing
# ---------------------------------------------------------------------------


def freeze(value: Any) -> Any:
    """Return a deep read-only copy (mappings -> MappingProxyType, lists -> tuples)."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    return value


def thaw(value: Any) -> Any:
    """Return a plain JSON-compatible deep copy of a frozen structure."""
    if isinstance(value, Mapping):
        return {k: thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [thaw(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# Schema validation (meta-validation of the schema itself)
# ---------------------------------------------------------------------------


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_schema(schema: Any, where: str, *, bounded: bool, depth: int) -> None:
    if depth > MAX_SCHEMA_DEPTH:
        raise ToolDefinitionError(f"{where}: schema nesting is deeper than {MAX_SCHEMA_DEPTH}")
    if not isinstance(schema, Mapping):
        raise ToolDefinitionError(f"{where}: schema must be an object")
    kind = schema.get("type")
    if not isinstance(kind, str) or kind not in _KEYWORDS_BY_TYPE:
        raise ToolDefinitionError(f"{where}: unsupported or missing type")
    allowed = _COMMON_KEYWORDS | _KEYWORDS_BY_TYPE[kind]
    unknown = sorted(set(schema) - allowed)
    if unknown:
        raise ToolDefinitionError(f"{where}: unsupported schema keyword(s) {unknown}")
    if "description" in schema and (
        not isinstance(schema["description"], str) or len(schema["description"]) > MAX_DESCRIPTION_CHARS
    ):
        raise ToolDefinitionError(f"{where}: description must be text of at most {MAX_DESCRIPTION_CHARS} chars")

    if kind == "object":
        if schema.get("additionalProperties") is not False:
            raise ToolDefinitionError(f"{where}: objects must be closed (additionalProperties: false)")
        properties = schema.get("properties", {})
        if not isinstance(properties, Mapping):
            raise ToolDefinitionError(f"{where}: properties must be an object")
        if len(properties) > MAX_PROPERTIES:
            raise ToolDefinitionError(f"{where}: more than {MAX_PROPERTIES} properties")
        for key, sub in properties.items():
            if not isinstance(key, str) or not _PROPERTY_RE.match(key):
                raise ToolDefinitionError(f"{where}: invalid property name")
            _check_schema(sub, f"{where}.{key}", bounded=bounded, depth=depth + 1)
        required = schema.get("required", ())
        if not isinstance(required, (list, tuple)) or not all(isinstance(r, str) for r in required):
            raise ToolDefinitionError(f"{where}: required must be a list of property names")
        if len(set(required)) != len(required) or not set(required) <= set(properties):
            raise ToolDefinitionError(f"{where}: required names must be unique declared properties")
    elif kind == "string":
        max_length = schema.get("maxLength")
        if bounded and max_length is None:
            raise ToolDefinitionError(f"{where}: strings must declare maxLength")
        if max_length is not None and (not _is_int(max_length) or not 1 <= max_length <= MAX_ARG_STRING_CHARS):
            raise ToolDefinitionError(f"{where}: maxLength must be 1..{MAX_ARG_STRING_CHARS}")
        min_length = schema.get("minLength", 0)
        if not _is_int(min_length) or min_length < 0 or (max_length is not None and min_length > max_length):
            raise ToolDefinitionError(f"{where}: invalid minLength")
        pattern = schema.get("pattern")
        if pattern is not None:
            if not isinstance(pattern, str) or len(pattern) > MAX_PATTERN_CHARS:
                raise ToolDefinitionError(f"{where}: pattern must be text of at most {MAX_PATTERN_CHARS} chars")
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ToolDefinitionError(f"{where}: invalid pattern") from exc
    elif kind in {"integer", "number"}:
        lo, hi = schema.get("minimum"), schema.get("maximum")
        if bounded and (lo is None or hi is None):
            raise ToolDefinitionError(f"{where}: numbers must declare minimum and maximum")
        for bound in (lo, hi):
            if bound is None:
                continue
            valid = _is_int(bound) if kind == "integer" else (
                (_is_int(bound) or isinstance(bound, float)) and math.isfinite(bound)
            )
            if not valid or abs(bound) > MAX_ARG_INT_ABS:
                raise ToolDefinitionError(f"{where}: numeric bounds must be finite and at most {MAX_ARG_INT_ABS}")
        if lo is not None and hi is not None and lo > hi:
            raise ToolDefinitionError(f"{where}: minimum is greater than maximum")
    elif kind == "array":
        if "items" not in schema:
            raise ToolDefinitionError(f"{where}: arrays must declare items")
        max_items = schema.get("maxItems")
        if bounded and max_items is None:
            raise ToolDefinitionError(f"{where}: arrays must declare maxItems")
        if max_items is not None and (not _is_int(max_items) or not 0 <= max_items <= MAX_ARG_ARRAY_ITEMS):
            raise ToolDefinitionError(f"{where}: maxItems must be 0..{MAX_ARG_ARRAY_ITEMS}")
        min_items = schema.get("minItems", 0)
        if not _is_int(min_items) or min_items < 0 or (max_items is not None and min_items > max_items):
            raise ToolDefinitionError(f"{where}: invalid minItems")
        _check_schema(schema["items"], f"{where}[]", bounded=bounded, depth=depth + 1)

    if "enum" in schema:
        values = schema["enum"]
        if not isinstance(values, (list, tuple)) or not values or len(values) > MAX_ENUM_VALUES:
            raise ToolDefinitionError(f"{where}: enum must be a non-empty list of at most {MAX_ENUM_VALUES}")
        for value in values:
            try:
                validate_value(schema, value, where)
            except ArgumentError as exc:
                raise ToolDefinitionError(f"{where}: enum value does not match the schema") from exc
    if "default" in schema:
        try:
            validate_value(schema, schema["default"], where)
        except ArgumentError as exc:
            raise ToolDefinitionError(f"{where}: default does not match the schema") from exc


def validate_argument_schema(schema: Any) -> None:
    """Reject argument schemas that are not closed, bounded objects."""
    if not isinstance(schema, Mapping) or schema.get("type") != "object":
        raise ToolDefinitionError("arguments: the argument schema must be an object")
    _check_schema(schema, "arguments", bounded=True, depth=1)


def validate_result_schema(schema: Any) -> None:
    """Reject result schemas that are open or untyped."""
    if not isinstance(schema, Mapping) or schema.get("type") != "object":
        raise ToolDefinitionError("result: the result schema must be an object")
    _check_schema(schema, "result", bounded=False, depth=1)


# ---------------------------------------------------------------------------
# Value validation (arguments and results)
# ---------------------------------------------------------------------------


class ArgumentError(ValueError):
    """A value does not match its schema. ``field`` names the offending field."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason


def validate_value(schema: Mapping[str, Any], value: Any, where: str = "arguments") -> Any:
    """Validate ``value`` against a (validated) schema; return it with defaults applied.

    Error reasons name the field and the rule only; values are never echoed.
    """
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, Mapping):
            raise ArgumentError(where, "must be an object")
        properties = schema.get("properties", {})
        extra = sorted(k for k in value if k not in properties)
        if extra:
            raise ArgumentError(f"{where}.{extra[0]}" if _PROPERTY_RE.match(str(extra[0])) else where,
                                "is not an accepted argument")
        out: dict[str, Any] = {}
        for key, sub in properties.items():
            if key in value:
                out[key] = validate_value(sub, value[key], f"{where}.{key}")
            elif "default" in sub:
                out[key] = thaw(sub["default"])
            elif key in schema.get("required", ()):
                raise ArgumentError(f"{where}.{key}", "is required")
        return out
    if kind == "string":
        if not isinstance(value, str):
            raise ArgumentError(where, "must be a string")
        if len(value) < schema.get("minLength", 0):
            raise ArgumentError(where, "is too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ArgumentError(where, f"is longer than {schema['maxLength']} characters")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            raise ArgumentError(where, "has an invalid format")
    elif kind == "integer":
        if not _is_int(value):
            raise ArgumentError(where, "must be an integer")
    elif kind == "number":
        if not (_is_int(value) or isinstance(value, float)) or (isinstance(value, float) and not math.isfinite(value)):
            raise ArgumentError(where, "must be a finite number")
    elif kind == "boolean":
        if not isinstance(value, bool):
            raise ArgumentError(where, "must be true or false")
    elif kind == "null":
        if value is not None:
            raise ArgumentError(where, "must be null")
    elif kind == "array":
        if not isinstance(value, (list, tuple)):
            raise ArgumentError(where, "must be a list")
        if len(value) < schema.get("minItems", 0):
            raise ArgumentError(where, "has too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ArgumentError(where, f"has more than {schema['maxItems']} items")
        value = [validate_value(schema["items"], item, f"{where}[{i}]") for i, item in enumerate(value)]
    else:
        raise ArgumentError(where, "has an unsupported schema type")

    if kind in {"integer", "number"}:
        if "minimum" in schema and value < schema["minimum"]:
            raise ArgumentError(where, f"must be at least {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ArgumentError(where, f"must be at most {schema['maximum']}")
    if "enum" in schema and value not in schema["enum"]:
        raise ArgumentError(where, "is not one of the accepted values")
    return value


# ---------------------------------------------------------------------------
# ToolDefinition
# ---------------------------------------------------------------------------


ToolHandler = Callable[..., Mapping[str, Any]]


@dataclass(frozen=True)
class ToolDefinition:
    """One structured tool (§8.1). Frozen and validated on construction."""

    name: str
    tool_version: int
    description: str
    arguments_schema: Mapping[str, Any]
    result_schema: Mapping[str, Any]
    permission: PermissionClass
    trust: TrustClass
    availability: Availability
    timeout_s: float
    limits: ToolLimits = field(default_factory=ToolLimits)
    side_effect: SideEffect = SideEffect.NONE
    plugin_id: str = ""
    source_kind: str = "tool"
    handler: ToolHandler | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _NAME_RE.match(self.name):
            raise ToolDefinitionError("name must be snake_case (2-48 chars)")
        if not _is_int(self.tool_version) or self.tool_version < 1:
            raise ToolDefinitionError("tool_version must be a positive major version")
        if not isinstance(self.description, str) or not 1 <= len(self.description) <= MAX_DESCRIPTION_CHARS:
            raise ToolDefinitionError(f"description must be 1..{MAX_DESCRIPTION_CHARS} characters")
        for attr, enum in (
            ("permission", PermissionClass),
            ("trust", TrustClass),
            ("availability", Availability),
            ("side_effect", SideEffect),
        ):
            value = getattr(self, attr)
            try:
                object.__setattr__(self, attr, enum(value))
            except ValueError as exc:
                raise ToolDefinitionError(f"{attr} {value!r} is not allowed") from exc
        network_perm = self.permission in _NETWORK_PERMISSIONS
        if network_perm != (self.side_effect is SideEffect.NETWORK):
            raise ToolDefinitionError("network permission and network side effect must go together")
        if network_perm and self.trust is not TrustClass.UNTRUSTED_EXTERNAL:
            raise ToolDefinitionError("network tools must produce untrusted_external output")
        if isinstance(self.timeout_s, bool) or not isinstance(self.timeout_s, (int, float)):
            raise ToolDefinitionError("timeout_s must be a number")
        if not math.isfinite(self.timeout_s) or not 0 < self.timeout_s <= MAX_TIMEOUT_S:
            raise ToolDefinitionError(f"timeout_s must be > 0 and <= {MAX_TIMEOUT_S:g}")
        if not isinstance(self.limits, ToolLimits):
            raise ToolDefinitionError("limits must be a ToolLimits")
        if self.plugin_id and not _PLUGIN_ID_RE.match(self.plugin_id):
            raise ToolDefinitionError("plugin_id must look like 'builtin.name'")
        if self.availability is Availability.AVAILABLE and not callable(self.handler):
            raise ToolDefinitionError("an available tool needs a handler")
        validate_argument_schema(self.arguments_schema)
        validate_result_schema(self.result_schema)
        object.__setattr__(self, "arguments_schema", freeze(self.arguments_schema))
        object.__setattr__(self, "result_schema", freeze(self.result_schema))

    @property
    def id(self) -> str:
        """Canonical tool id, ``zoe.<name>``."""
        return f"{TOOL_ID_PREFIX}{self.name}"

    @property
    def available(self) -> bool:
        return self.availability is Availability.AVAILABLE

    @property
    def version_string(self) -> str:
        return str(self.tool_version)

    def validate_arguments(self, arguments: Any) -> dict[str, Any]:
        """Validate model arguments against the closed schema; apply defaults."""
        return validate_value(self.arguments_schema, arguments, "arguments")

    def validate_result(self, payload: Any) -> dict[str, Any]:
        """Validate a tool payload against the result schema."""
        return validate_value(self.result_schema, payload, "result")

    def wire_schema(self) -> dict[str, Any]:
        """Qwen ``tools=`` function schema (wire name is the bare tool name, §10.1)."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": thaw(self.arguments_schema),
            },
        }
