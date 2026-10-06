"""Phase B2 web authorization and egress policy for Zoe AI.

This module is the single authoritative decision point for web access
(ZOE_PHASE_A1_DESIGN.md §6, approved Decision 2 = Option A).

Contract:

- Every turn starts with web access denied.
- Only the *current user message* can authorize web access, and only when it
  explicitly instructs Zoe to use the web ("search the web for ...", "look this
  up online", "browse the internet for ...", ...). Keywords such as "latest",
  "version", "release", "documentation", "compare", "current" or "pdf" never
  authorize anything on their own.
- Quoted text, code blocks, inline code, comment lines and pasted content are
  never treated as the user's instruction. Negated web wording anywhere in the
  message denies web access for the whole turn (fail closed on mixed signals).
- The authorization is held in a turn-scoped context variable only: it is never
  written to disk, never carried to the next turn and never survives restart.
- Only a narrow query extracted from the explicit request may leave the machine
  (<= 200 chars, <= 32 words, one line). The raw message, history, memory,
  retrieved content and tool output are never sent. If no clean query can be
  extracted nothing is sent and the turn is ``web_not_authorized`` (internal
  diagnostic ``query_unbuildable``).
- If a secret or private data item (email, phone number, IP address, local
  path, private hostname, high-entropy string, redaction marker) appears
  *anywhere* in the current message the whole web operation is blocked
  (``egress_blocked_sensitive``). Secrets are never stripped, redacted
  and forwarded, stored, logged or echoed; only a category is reported.
- ``ZOE_OFFLINE=1`` is a hard block, re-checked at call time. Its public
  error type is ``network_unavailable`` (internal diagnostic ``offline_mode``).
- Public error types are exactly the eight canonical ones in
  ``tools.result_envelope.ErrorType``. Finer distinctions (offline, no buildable
  query, missing provider package, unclassified provider error) exist only as
  internal ``diagnostic`` / ``detail`` codes, never as statuses.
- At most one provider search runs per turn; every web path in the same turn
  shares that single outcome. Page fetches are limited to URLs returned by this
  turn's search.

The low-level network functions (``web.search.search_web`` and
``web.reader.read_webpage``) consult this module before any network access, so
this boundary can later become the PolicyGate in front of a structured
``web_search`` tool call.
"""

from __future__ import annotations

import contextvars
import ipaddress
import logging
import math
import os
import re
import threading
import uuid
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator
from urllib.parse import urlparse

from tools.result_envelope import ErrorType, ResultStatus, bound_result, error_envelope
from tools.secret_scan import REDACTED_LINE, contains_private_key, line_has_secret
from tools.session_markers import (
    CATEGORY_CAPACITY,
    CATEGORY_REDACTED,
    CATEGORY_SENSITIVE_PATH,
    match_session_markers,
)
from training.schema.privacy import scan_text as _privacy_scan_text

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("zoe.web.audit")

# Limits from ZOE_PHASE_A1_DESIGN.md §6.3 / §24, or existing implementation values.
MAX_QUERY_CHARS = 200  # §6.3
MAX_QUERY_WORDS = 32  # §6.3
NEAR_COPY_MESSAGE_CHARS = 200  # §6.3
NEAR_COPY_RATIO = 0.8  # §6.3
MAX_RESULTS = 5  # §24 (also the existing search_web default)
MAX_TITLE_CHARS = 200  # §24
MAX_SNIPPET_CHARS = 300  # §24
MAX_PAGE_FETCHES = 3  # existing retriever default max_pages
HIGH_ENTROPY_MIN_CHARS = 24  # §6.4
OFFLINE_ENV = "ZOE_OFFLINE"

UNTRUSTED_EXTERNAL = "untrusted_external"

FALLBACK_COULD_NOT_SEARCH = (
    "I couldn't reach the web, so this is from my own knowledge and may be out of date."
)


# Structured vocabulary: the universal result envelope (A.1 §8.3/§24.4) and the
# eight canonical error types. No web-specific synonyms exist.
DENIED_ERROR_TYPES = frozenset(
    {
        ErrorType.WEB_NOT_AUTHORIZED,
        ErrorType.EGRESS_BLOCKED_SENSITIVE,
    }
)
COULD_NOT_SEARCH_ERROR_TYPES = frozenset(
    {
        ErrorType.NETWORK_UNAVAILABLE,
        ErrorType.TIMEOUT,
        ErrorType.RESULT_UNREPRESENTABLE,
    }
)

# Internal diagnostic codes (never statuses, never shown as error types, never
# contain message text). They let Zoe word its reply precisely while the public
# error type stays canonical.
DIAG_OFFLINE = "offline_mode"  # public: network_unavailable
DIAG_QUERY_UNBUILDABLE = "query_unbuildable"  # public: web_not_authorized
DIAG_PROVIDER_MISSING = "provider_package_missing"  # public: network_unavailable
DIAG_PROVIDER_ERROR = "provider_error"  # public: network_unavailable

CATEGORY_LABELS = {
    "private_key": "a private key",
    "credential": "credential material (an API key, token, password or similar)",
    "high_entropy_string": "a long random-looking string that may be a secret",
    "redacted_content": "content that was redacted because it contained a possible secret",
    CATEGORY_REDACTED: "content that was redacted earlier in this session",
    CATEGORY_SENSITIVE_PATH: "a protected file path that was refused earlier in this session",
    CATEGORY_CAPACITY: "too much sensitive content handled earlier in this session to check safely",
    "email_address": "an email address",
    "phone_number": "a phone number",
    "ip_address": "an IP address",
    "local_path": "a local file path",
    "private_host": "a private or local hostname",
}


@dataclass(frozen=True)
class WebDecision:
    """The single per-turn web authorization decision. Never holds message text.

    ``error_type is None`` means the turn is authorized (A.1 §13 decision
    ``allow``); otherwise the decision is ``deny`` with that canonical type.
    """

    error_type: ErrorType | None
    explicit_intent: bool = False
    query: str | None = None
    categories: tuple[str, ...] = ()
    reason: str = ""
    # Internal diagnostic code (``DIAG_*``); not a status.
    diagnostic: str = ""

    @property
    def allowed(self) -> bool:
        return self.error_type is None and bool(self.query)

    @property
    def verdict(self) -> str:
        return "allow" if self.allowed else "deny"


NOT_AUTHORIZED = WebDecision(ErrorType.WEB_NOT_AUTHORIZED, reason="no_turn")


@dataclass(frozen=True)
class WebItem:
    """One bounded search result item (A.1 §6.6)."""

    rank: int
    title: str
    url: str
    snippet: str
    source_domain: str


@dataclass(frozen=True)
class SearchOutcome:
    """Typed result of a gated search. ``trust`` is always untrusted_external."""

    status: ResultStatus
    error_type: ErrorType | None = None
    query: str | None = None
    items: tuple[WebItem, ...] = ()
    retrieved_at: str = ""
    trust: str = UNTRUSTED_EXTERNAL
    truncated: bool = False
    # Internal diagnostic code (``DIAG_*``); not a status, not in the envelope.
    detail: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status is ResultStatus.SUCCESS and bool(self.items)

    @property
    def searched(self) -> bool:
        """True only when the provider call actually completed."""
        return self.succeeded or self.error_type is ErrorType.NO_RESULTS

    def as_search_results(self) -> list[dict[str, str]]:
        """Return the legacy ``WebSearchResult`` shape used by the retriever."""
        return [{"title": i.title, "url": i.url, "body": i.snippet} for i in self.items]

    def to_envelope(self) -> dict:
        """The A.1 §6.6 ``web_search`` tool_result envelope for this outcome."""
        source = {"kind": "web", "provider": "duckduckgo"}
        if self.succeeded:
            return bound_result(
                "web_search",
                {
                    "query": self.query,
                    "retrieved_at": self.retrieved_at,
                    "items": [
                        {
                            "rank": i.rank,
                            "title": i.title,
                            "url": i.url,
                            "snippet": i.snippet,
                            "source_domain": i.source_domain,
                        }
                        for i in self.items
                    ],
                },
                trust=UNTRUSTED_EXTERNAL,
                source=source,
            )
        return error_envelope(
            "web_search",
            self.status,
            self.error_type or ErrorType.NETWORK_UNAVAILABLE,
            trust=UNTRUSTED_EXTERNAL,
            source=source,
        )


def _denied(error_type: ErrorType, query: str | None = None, detail: str = "") -> SearchOutcome:
    return SearchOutcome(ResultStatus.DENIED, error_type, query=query, detail=detail)


@dataclass(frozen=True)
class WebState:
    """Final structured web state of the current turn (status + error.type)."""

    status: ResultStatus | None
    error_type: ErrorType | None = None
    # Internal diagnostic code (``DIAG_*``); excluded from equality.
    detail: str = field(default="", compare=False)

    @property
    def denied(self) -> bool:
        return self.status is ResultStatus.DENIED

    @property
    def label(self) -> str:
        if self.error_type is not None:
            return self.error_type.value
        return self.status.value if self.status is not None else "not_run"


@dataclass(frozen=True)
class FetchDecision:
    """Gate decision for one page fetch (A.1 §6.3 URL provenance)."""

    allowed: bool
    status: ResultStatus | None = None
    error_type: ErrorType | None = None
    reason: str = ""


# ---------------------------------------------------------------------------
# Offline mode
# ---------------------------------------------------------------------------


def is_offline() -> bool:
    """Return True when ZOE_OFFLINE is set to a truthy value."""
    return os.environ.get(OFFLINE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Explicit intent detection (current user message only)
# ---------------------------------------------------------------------------

_QUOTE_OPEN = "\ue000"
_QUOTE_CLOSE = "\ue001"
_CODE_MARK = "\ue002"

_FENCED = re.compile(r"(```|~~~).*?(?:\1|\Z)", re.S)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_DOUBLE_QUOTED = re.compile(r"[\"“”„«»]([^\"“”„«»\n]{0,400})[\"“”„«»]")
_SINGLE_QUOTED = re.compile(r"(?<!\w)['‘’]([^'‘’\n]{1,400})['‘’](?!\w)")
_COMMENT_OR_QUOTE_LINE = re.compile(r"^\s*(?:#|//|--|/\*|\*|;|<!--|>|%|rem\s)", re.I)
_INDENTED_LINE = re.compile(r"^(?: {4}|\t)")
_PASTE_INTRO = re.compile(
    r"(?i)\b(?:code|snippet|file|log|logs|output|error|errors|traceback|stack\s*trace|text|"
    r"content|contents|message|email|transcript|script|config|document|json|yaml|data|paste)"
    r"\s*:\s*$"
)

_LEAD = r"(?:(?:please|pls|zoe|hey|ok|okay|now|also|then|and|so|just|quickly|kindly)[,\s]+)*"
_ASK = (
    r"(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?"
    r"|i\s+(?:want|need|would\s+like|['’]d\s+like)\s+you\s+to\s+"
    r"|go\s+ahead\s+and\s+|let['’]?s\s+|try\s+(?:to\s+)?)?"
)
_WEB_TARGET = r"(?:(?:on\s+)?(?:the\s+)?(?:web|internet|net)|online)"
_ONLINE_SUFFIX = (
    r"(?:online|on\s+the\s+(?:web|internet|net)|on\s+google|from\s+the\s+(?:web|internet)"
    r"|using\s+the\s+(?:web|internet)|via\s+(?:the\s+)?(?:web|internet))"
)
_TAIL = r"(?:\s*,?\s*(?:please|for\s+me|right\s+now|now))*\s*[.!?]*\s*"

# Forms where the web phrase comes first and the object follows.
_VERB_FIRST = re.compile(
    r"^" + _LEAD + _ASK + r"(?:"
    r"search\s+" + _WEB_TARGET + r"(?:\s+(?:for|about|on|regarding))?"
    r"|(?:do|run|perform|make)\s+(?:an?\s+)?(?:web|internet|online|google)\s+search"
    r"(?:\s+(?:for|on|about))?"
    r"|google(?:\s+for)?"
    r"|browse\s+" + _WEB_TARGET + r"(?:\s+(?:for|about|on))?"
    r"|check\s+" + _WEB_TARGET + r"(?:\s+(?:for|about|on|whether|if))?"
    r"|look\s+(?:on|at)\s+" + _WEB_TARGET + r"(?:\s+(?:for|about))?"
    r"|use\s+(?:the\s+)?(?:web|internet)(?:\s+search)?\s+(?:to\s+(?:find|look\s+up|check|search\s+for|get)"
    r"|for)"
    r")(?=\s|$|[.!?,:])(?P<obj>.*)$",
    re.I | re.S,
)
# Forms where the object sits between the verb and the web suffix.
_OBJECT_FIRST = re.compile(
    r"^" + _LEAD + _ASK + r"(?:"
    r"(?:look\s+up|search\s+for|search|find|get|fetch|check|research|pull\s+up|look\s+for)\s+"
    r"(?P<obj>.+?)\s+" + _ONLINE_SUFFIX +
    r"|look\s+(?P<obj2>\S.*?)\s+up\s+" + _ONLINE_SUFFIX +
    r")" + _TAIL + r"$",
    re.I | re.S,
)
_CLAUSE_BOUNDARY = re.compile(r",\s*|;\s*|\s+(?:and\s+then|then|and\s+also|also|and|but|plus)\s+", re.I)
_REPORTING = re.compile(
    r"(?i)\b(?:said|says|say|saying|told\s+\w+|tells\s+\w+|asked|asks|wrote|writes|replied|"
    r"suggested|meant|means)\s*,?\s*$"
)
_NEGATED_WEB = re.compile(
    r"(?i)\b(?:don['’]?t|do\s+not|doesn['’]?t|never|no\s+need\s+to|not|without|stop|avoid|"
    r"refrain\s+from|no|nor)\b[^.!?;,\n]{0,40}?"
    r"\b(?:search\w*|brows\w*|googl\w*|look\w*\s+(?:\w+\s+)?up|web|internet|online)\b"
)
_OBJECT_CUT = re.compile(
    r",?\s+(?:and\s+then|then|and\s+(?=(?:explain|tell|summari[sz]e|write|give|show|compare|"
    r"list|describe|help|answer|translate)\b))",
    re.I,
)
_OBJECT_TRIM_TAIL = re.compile(
    r"(?:\s*,?\s*(?:please|for\s+me|right\s+now|now|" + _ONLINE_SUFFIX + r"))+\s*$", re.I
)
_OBJECT_TRIM_HEAD = re.compile(r"^\s*(?:[:\-–—]\s*|(?:for|about|on|regarding)\s+)", re.I)
_FILLER_WORDS = frozenset(
    {
        "this", "that", "it", "them", "these", "those", "something", "anything", "stuff",
        "things", "thing", "for", "me", "please", "info", "information", "details", "more",
        "the", "a", "an", "about", "up", "on", "now", "online", "web", "internet", "out",
        "what", "whatever", "everything",
    }
)
_DEICTIC = frozenset({"this", "that", "these", "those", "it", "its", "his", "her", "their"})


@dataclass(frozen=True)
class _Intent:
    explicit: bool
    reason: str
    raw_object: str = ""
    quotes: tuple[str, ...] = ()


def _mask_message(message: str) -> tuple[str, list[str]]:
    """Mask code and quoted text; return masked text and quoted spans."""
    text = message.replace("\r\n", "\n").replace("\r", "\n")
    text = _FENCED.sub(f" {_CODE_MARK} ", text)
    text = _INLINE_CODE.sub(f" {_CODE_MARK} ", text)
    quotes: list[str] = []

    def _keep(match: re.Match[str]) -> str:
        quotes.append(match.group(1))
        return f"{_QUOTE_OPEN}{len(quotes) - 1}{_QUOTE_CLOSE}"

    text = _DOUBLE_QUOTED.sub(_keep, text)
    text = _SINGLE_QUOTED.sub(_keep, text)

    kept_lines: list[str] = []
    in_paste = False
    for line in text.split("\n"):
        if in_paste:
            kept_lines.append(_CODE_MARK)
            continue
        if _COMMENT_OR_QUOTE_LINE.match(line) or _INDENTED_LINE.match(line):
            kept_lines.append(_CODE_MARK)
            continue
        kept_lines.append(line)
        if _PASTE_INTRO.search(line):
            in_paste = True
    return "\n".join(kept_lines), quotes


def _sentences(masked: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", masked)
    return [p.strip() for p in parts if p and p.strip()]


def _clause_starts(sentence: str) -> list[int]:
    starts = [0]
    for match in _CLAUSE_BOUNDARY.finditer(sentence):
        if not _REPORTING.search(sentence[: match.start()]):
            starts.append(match.end())
    return starts


def _match_clause(clause: str) -> str | None:
    """Return the request object if the clause is an explicit web instruction."""
    clause = clause.strip()
    if not clause or clause.startswith(_CODE_MARK):
        return None
    m = _OBJECT_FIRST.match(clause)
    if m:
        return m.group("obj") or m.group("obj2") or ""
    m = _VERB_FIRST.match(clause)
    if m:
        return m.group("obj") or ""
    return None


def _detect_intent(message: str) -> _Intent:
    if not message or not message.strip():
        return _Intent(False, "empty")
    masked, quotes = _mask_message(message)
    if _NEGATED_WEB.search(masked):
        return _Intent(False, "negated")
    for sentence in _sentences(masked):
        for start in _clause_starts(sentence):
            obj = _match_clause(sentence[start:])
            if obj is not None:
                return _Intent(True, "explicit", raw_object=obj, quotes=tuple(quotes))
    return _Intent(False, "no_explicit_web_instruction")


def has_explicit_web_intent(message: str) -> bool:
    """Return True when the current message explicitly instructs Zoe to use the web."""
    return _detect_intent(message).explicit


# ---------------------------------------------------------------------------
# Query construction
# ---------------------------------------------------------------------------


def _build_query(intent: _Intent, message: str) -> tuple[str | None, str]:
    obj = _OBJECT_CUT.split(intent.raw_object, maxsplit=1)[0]
    if _CODE_MARK in obj:
        return None, "object_contains_code_or_pasted_content"

    def _restore(match: re.Match[str]) -> str:
        index = int(match.group(1))
        return intent.quotes[index] if index < len(intent.quotes) else ""

    obj = re.sub(f"{_QUOTE_OPEN}(\\d+){_QUOTE_CLOSE}", _restore, obj)
    obj = obj.replace("`", "")
    obj = re.sub(r"\s+", " ", obj).strip()
    obj = _OBJECT_TRIM_HEAD.sub("", obj)
    obj = _OBJECT_TRIM_TAIL.sub("", obj).strip(" \t.,;:!?-–—")
    obj = obj.strip()

    if not obj or "\n" in obj:
        return None, "empty_object"
    words = re.findall(r"[\w'’.+#-]+", obj.lower())
    if not words or all(w in _FILLER_WORDS for w in words):
        return None, "object_is_only_pronouns_or_filler"
    if words[0] in _DEICTIC and len(words) <= 3:
        return None, "object_refers_to_unstated_context"
    if len(obj) > MAX_QUERY_CHARS or len(obj.split()) > MAX_QUERY_WORDS:
        return None, "object_too_long"
    normalized_message = re.sub(r"\s+", " ", message).strip()
    if (
        len(normalized_message) > NEAR_COPY_MESSAGE_CHARS
        and len(obj) / max(1, len(normalized_message)) > NEAR_COPY_RATIO
    ):
        return None, "near_copy_of_message"
    return obj, "ok"


# ---------------------------------------------------------------------------
# Sensitive-content scanning (reuses B1 secret_scan + training privacy scanner)
# ---------------------------------------------------------------------------

_NATURAL_LANGUAGE_CREDENTIAL = re.compile(
    r"(?i)\b(?:password|passcode|passphrase|passwd|pin|api[\s_-]?key|secret(?:\s+key)?|"
    r"access\s+token|auth\s+token|bearer\s+token|token|private\s+key)\s+(?:is|was|=|:)\s+"
    r"['\"]?(?P<value>[^\s'\"]{4,})"
)
_EXTRA_CREDENTIAL_PATTERNS = (
    re.compile(r"(?i)\b(?:AccountKey|SharedAccessKey|SharedAccessSignature|aws_session_token)\s*=\s*\S{8,}"),
    re.compile(r"(?i)\b(?:x-api-key|api-key|x-auth-token)\s*:\s*\S{8,}"),
)
_LONG_RUN = re.compile(r"[A-Za-z0-9+/=]{%d,}" % HIGH_ENTROPY_MIN_CHARS)
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6 = re.compile(r"(?i)\b(?:[0-9a-f]{1,4}:){3,7}[0-9a-f]{1,4}\b")
_LOCAL_PATH = re.compile(
    r"(?i)(?:^|[\s(\"'=])(?:~[/\\]|\.{1,2}[/\\]|file://|[a-z]:[\\/]|\\\\[\w.-]+\\"
    r"|/(?:home|users|etc|var|tmp|root|opt|mnt|workspace|usr|srv|proc|dev|private|volumes|library)\b)"
)
_PRIVATE_HOST = re.compile(
    r"(?i)\b(?:localhost|[\w-]+\.(?:local|internal|lan|corp|home|intranet|localdomain))\b"
)


def _shannon_entropy(text: str) -> float:
    counts = Counter(text)
    length = len(text)
    return -sum((n / length) * math.log2(n / length) for n in counts.values())


def _looks_secret_value(value: str) -> bool:
    """A natural-language credential value: >= 6 chars, not code, has a digit or symbol."""
    value = value.rstrip(".,;:!?")
    if len(value) < 6 or re.search(r"[()\[\]{}<>]", value):
        return False
    return bool(re.search(r"[\d\W_]", value))


# Markers B1 filesystem tools emit when they redacted a secret. A message that
# carries them is (pasted) redacted tool output: fail closed without needing any
# record of the original secret value (no secret store exists or is created).
_REDACTION_MARKERS = (REDACTED_LINE, "[redacted ", "line(s) containing possible secrets]")


def scan_message_secrets(message: str) -> tuple[str, ...]:
    """Return secret categories found anywhere in the message (values never returned)."""
    categories: list[str] = []
    if contains_private_key(message):
        categories.append("private_key")
    if any(marker in message for marker in _REDACTION_MARKERS):
        categories.append("redacted_content")
    lines = message.replace("\r\n", "\n").split("\n")
    credential = any(line_has_secret(line) for line in lines)
    if not credential:
        credential = any(p.search(message) for p in _EXTRA_CREDENTIAL_PATTERNS)
    if not credential:
        credential = any(
            _looks_secret_value(m.group("value")) for m in _NATURAL_LANGUAGE_CREDENTIAL.finditer(message)
        )
    if credential:
        categories.append("credential")
    for run in _LONG_RUN.findall(message):
        if (
            re.search(r"[A-Za-z]", run)
            and re.search(r"\d", run)
            and _shannon_entropy(run) >= 3.5
        ):
            categories.append("high_entropy_string")
            break
    return tuple(dict.fromkeys(categories))


def scan_query_sensitive(query: str) -> tuple[str, ...]:
    """Return private-data categories in an outbound query (A.1 §6.4)."""
    categories: list[str] = []
    reasons = _privacy_scan_text(query).reasons
    if "email_address" in reasons:
        categories.append("email_address")
    if "possible_phone" in reasons:
        categories.append("phone_number")
    if _IPV4.search(query) or _IPV6.search(query):
        categories.append("ip_address")
    if _LOCAL_PATH.search(query):
        categories.append("local_path")
    if _PRIVATE_HOST.search(query):
        categories.append("private_host")
    return tuple(categories)


# ---------------------------------------------------------------------------
# The single decision
# ---------------------------------------------------------------------------


def evaluate_web_request(message: str) -> WebDecision:
    """Return the one authoritative web decision for the current user message."""
    intent = _detect_intent(message)
    if not intent.explicit:
        return WebDecision(ErrorType.WEB_NOT_AUTHORIZED, reason=intent.reason)
    if is_offline():
        return WebDecision(
            ErrorType.NETWORK_UNAVAILABLE, explicit_intent=True, reason="offline", diagnostic=DIAG_OFFLINE
        )
    secret_categories = scan_message_secrets(message)
    if secret_categories:
        return WebDecision(
            ErrorType.EGRESS_BLOCKED_SENSITIVE,
            explicit_intent=True,
            categories=secret_categories,
            reason="secret_in_message",
        )
    # Private data (emails, phone numbers, IPs, local paths, private hosts)
    # anywhere in the current message blocks the whole operation too, not only
    # when it lands inside the extracted query (fail closed).
    private_categories = scan_query_sensitive(message)
    if private_categories:
        return WebDecision(
            ErrorType.EGRESS_BLOCKED_SENSITIVE,
            explicit_intent=True,
            categories=private_categories,
            reason="private_data_in_message",
        )
    # A.1 §6.4: content that was redacted, or a path refused as sensitive,
    # earlier in this session (keyed fingerprints; no raw values exist).
    session_categories = match_session_markers(message)
    if session_categories:
        return WebDecision(
            ErrorType.EGRESS_BLOCKED_SENSITIVE,
            explicit_intent=True,
            categories=session_categories,
            reason="previously_sensitive_content",
        )
    query, reason = _build_query(intent, message)
    if query is None:
        # Explicit intent alone authorizes nothing: authorization covers one
        # concrete narrow query, and none could be built (secrets were already
        # ruled out above), so nothing is authorized to leave.
        return WebDecision(
            ErrorType.WEB_NOT_AUTHORIZED, explicit_intent=True, reason=reason, diagnostic=DIAG_QUERY_UNBUILDABLE
        )
    query_categories = scan_query_sensitive(query)
    if query_categories:
        return WebDecision(
            ErrorType.EGRESS_BLOCKED_SENSITIVE,
            explicit_intent=True,
            categories=query_categories,
            reason="sensitive_query",
        )
    return WebDecision(None, explicit_intent=True, query=query, reason="explicit")


# ---------------------------------------------------------------------------
# Turn scope (in memory only)
# ---------------------------------------------------------------------------


@dataclass
class _WebTurn:
    turn_id: str
    decision: WebDecision
    lock: threading.Lock = field(default_factory=threading.Lock)
    outcome: SearchOutcome | None = None
    final_state: WebState | None = None
    allowed_urls: frozenset[str] = frozenset()
    used_urls: tuple[str, ...] = ()
    fetches: int = 0


_CURRENT_TURN: contextvars.ContextVar[_WebTurn | None] = contextvars.ContextVar(
    "zoe_web_turn", default=None
)


@contextmanager
def web_turn(message: str) -> Iterator[WebDecision]:
    """Scope one user turn: compute the decision once, discard it on exit."""
    decision = evaluate_web_request(message)
    turn = _WebTurn(turn_id=uuid.uuid4().hex[:12], decision=decision)
    if decision.explicit_intent and not decision.allowed:
        audit_logger.info(
            "web_decision turn=%s decision=deny error_type=%s categories=%s reason=%s",
            turn.turn_id,
            decision.error_type.value if decision.error_type else "-",
            ",".join(decision.categories) or "-",
            decision.reason,
        )
    token = _CURRENT_TURN.set(turn)
    try:
        yield decision
    finally:
        _CURRENT_TURN.reset(token)


def current_decision() -> WebDecision:
    turn = _CURRENT_TURN.get()
    return turn.decision if turn is not None else NOT_AUTHORIZED


def current_outcome() -> SearchOutcome | None:
    turn = _CURRENT_TURN.get()
    return turn.outcome if turn is not None else None


def current_web_state() -> WebState:
    """Final structured web state for this turn (the decision when nothing ran)."""
    turn = _CURRENT_TURN.get()
    if turn is None:
        return WebState(ResultStatus.DENIED, ErrorType.WEB_NOT_AUTHORIZED)
    if turn.final_state is not None:
        return turn.final_state
    if not turn.decision.allowed:
        return WebState(ResultStatus.DENIED, turn.decision.error_type, detail=turn.decision.diagnostic)
    return WebState(None)


def current_used_sources() -> list[tuple[str, str]]:
    """(title, url) of result pages that were read into context this turn."""
    turn = _CURRENT_TURN.get()
    if turn is None or turn.outcome is None:
        return []
    titles = {item.url: item.title for item in turn.outcome.items}
    return [(titles.get(url) or url, url) for url in turn.used_urls]


# ---------------------------------------------------------------------------
# The gate (every search and page fetch passes through here)
# ---------------------------------------------------------------------------


def _domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def _bound_outcome(outcome: SearchOutcome, limit: int) -> SearchOutcome:
    """Bound provider items through the universal result layer (§24)."""
    retrieved_at = outcome.retrieved_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    if outcome.status is not ResultStatus.SUCCESS:
        return SearchOutcome(
            outcome.status, outcome.error_type, query=outcome.query, retrieved_at=retrieved_at, detail=outcome.detail
        )
    raw_items = [
        {
            "rank": index,
            "title": item.title,
            "url": item.url,
            "snippet": item.snippet,
            "source_domain": item.source_domain or _domain(item.url),
        }
        for index, item in enumerate(outcome.items[:limit], start=1)
    ]
    if not raw_items:
        return SearchOutcome(ResultStatus.ERROR, ErrorType.NO_RESULTS, query=outcome.query, retrieved_at=retrieved_at)
    envelope = bound_result(
        "web_search",
        {"query": outcome.query, "retrieved_at": retrieved_at, "items": raw_items},
        trust=UNTRUSTED_EXTERNAL,
        source={"kind": "web", "provider": "duckduckgo"},
    )
    if envelope["status"] != ResultStatus.SUCCESS.value:
        return SearchOutcome(
            ResultStatus.ERROR, ErrorType.RESULT_UNREPRESENTABLE, query=outcome.query, retrieved_at=retrieved_at
        )
    items = tuple(
        WebItem(
            rank=i["rank"],
            title=i["title"],
            url=i["url"],
            snippet=i["snippet"],
            source_domain=i["source_domain"],
        )
        for i in envelope["result"]["items"]
    )
    return SearchOutcome(
        ResultStatus.SUCCESS,
        None,
        query=outcome.query,
        items=items,
        retrieved_at=retrieved_at,
        truncated=bool(envelope["truncated"]),
    )


def gated_search(requested_query: str | None = None, max_results: int = MAX_RESULTS) -> SearchOutcome:
    """Run at most one authorized provider search for the current turn.

    ``requested_query`` is never sent: only the query extracted from the
    current user message's explicit request can leave the machine.
    """
    turn = _CURRENT_TURN.get()
    if turn is None:
        logger.debug("Web search refused: no active user turn")
        return _denied(ErrorType.WEB_NOT_AUTHORIZED)
    if is_offline():
        return _denied(ErrorType.NETWORK_UNAVAILABLE, detail=DIAG_OFFLINE)
    decision = turn.decision
    if not decision.allowed:
        return _denied(decision.error_type or ErrorType.WEB_NOT_AUTHORIZED, detail=decision.diagnostic)

    with turn.lock:
        if turn.outcome is not None:
            return turn.outcome
        # Re-check session markers at call time (a tool may have redacted
        # content earlier in this same turn).
        if match_session_markers(decision.query or ""):
            audit_logger.info(
                "web_decision turn=%s decision=deny error_type=%s categories=session_marker",
                turn.turn_id,
                ErrorType.EGRESS_BLOCKED_SENSITIVE.value,
            )
            outcome = _denied(ErrorType.EGRESS_BLOCKED_SENSITIVE)
            turn.outcome = outcome
            turn.final_state = WebState(outcome.status, outcome.error_type)
            return outcome
        if requested_query is not None and requested_query.strip() != decision.query:
            logger.debug("Caller-supplied web query ignored; using the authorized query")
        limit = max(1, min(int(max_results or MAX_RESULTS), MAX_RESULTS))
        from web.search import provider_search

        try:
            raw = provider_search(decision.query, limit)
        except Exception as exc:  # provider must never raise past the gate
            logger.warning("Web provider raised unexpectedly: %s", type(exc).__name__)
            raw = SearchOutcome(
                ResultStatus.ERROR, ErrorType.NETWORK_UNAVAILABLE, query=decision.query, detail=DIAG_PROVIDER_ERROR
            )
        outcome = _bound_outcome(raw, limit)
        turn.outcome = outcome
        turn.final_state = WebState(outcome.status, outcome.error_type, detail=outcome.detail)
        turn.allowed_urls = frozenset(item.url for item in outcome.items if item.url) if outcome.succeeded else frozenset()
        audit_logger.info(
            "web_egress turn=%s source=user_turn query=%r status=%s error_type=%s results=%d",
            turn.turn_id,
            decision.query,
            outcome.status.value,
            outcome.error_type.value if outcome.error_type else "-",
            len(outcome.items),
        )
        return outcome


_PRIVATE_SUFFIXES = (".local", ".internal", ".lan", ".corp", ".home", ".intranet", ".localdomain", ".localhost", ".home.arpa")


def is_private_host(host: str) -> bool:
    """True for loopback, private, link-local, reserved IPs and local-only names."""
    host = (host or "").strip().strip("[]").lower().rstrip(".")
    if not host:
        return True
    if host == "localhost" or host.endswith(_PRIVATE_SUFFIXES) or "." not in host and ":" not in host:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def check_fetch_target(url: str) -> FetchDecision:
    """Static URL checks shared by first requests and redirects."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return FetchDecision(False, ResultStatus.DENIED, ErrorType.WEB_NOT_AUTHORIZED, "invalid_url")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return FetchDecision(False, ResultStatus.DENIED, ErrorType.WEB_NOT_AUTHORIZED, "invalid_url")
    if parsed.username is not None or parsed.password is not None:
        return FetchDecision(False, ResultStatus.DENIED, ErrorType.EGRESS_BLOCKED_SENSITIVE, "credentials_in_url")
    if is_private_host(parsed.hostname or ""):
        return FetchDecision(False, ResultStatus.DENIED, ErrorType.EGRESS_BLOCKED_SENSITIVE, "private_host")
    return FetchDecision(True)


def url_in_turn_results(url: str) -> bool:
    """True when ``url`` came, unmodified, from this turn's successful search."""
    turn = _CURRENT_TURN.get()
    if turn is None or not turn.decision.allowed or turn.outcome is None:
        return False
    if not turn.outcome.succeeded:
        return False
    return url in turn.allowed_urls


def authorize_fetch(url: str) -> FetchDecision:
    """Gate one page download (A.1 §6.3: only the URL from a prior result).

    Allowed only when (1) this turn has an authorized web search, (2) that
    search succeeded, (3) ``url`` is exactly a URL from its results (no
    rewriting, no added parameters), (4) the URL carries no credentials and
    does not point at a private or local host, (5) offline mode is off, and
    (6) the per-turn page budget is not exhausted.
    """
    turn = _CURRENT_TURN.get()
    if turn is None:
        return FetchDecision(False, ResultStatus.DENIED, ErrorType.WEB_NOT_AUTHORIZED, "no_turn")
    if is_offline():
        return FetchDecision(False, ResultStatus.DENIED, ErrorType.NETWORK_UNAVAILABLE, DIAG_OFFLINE)
    if not turn.decision.allowed:
        return FetchDecision(
            False, ResultStatus.DENIED, turn.decision.error_type or ErrorType.WEB_NOT_AUTHORIZED, "turn_not_authorized"
        )
    with turn.lock:
        if turn.outcome is None:
            return FetchDecision(False, ResultStatus.DENIED, ErrorType.WEB_NOT_AUTHORIZED, "no_search_yet")
        if not turn.outcome.succeeded:
            return FetchDecision(False, ResultStatus.DENIED, ErrorType.WEB_NOT_AUTHORIZED, "search_not_successful")
        if url not in turn.allowed_urls:
            return FetchDecision(False, ResultStatus.DENIED, ErrorType.WEB_NOT_AUTHORIZED, "url_not_from_results")
        target = check_fetch_target(url)
        if not target.allowed:
            return target
        if turn.fetches >= MAX_PAGE_FETCHES:
            return FetchDecision(False, ResultStatus.BUDGET_EXCEEDED, ErrorType.BUDGET_EXCEEDED, "page_budget")
        turn.fetches += 1
        return FetchDecision(True)


def record_pages_used(urls: list[str]) -> None:
    """Record which result pages made it into context; marks fetch_failed if none."""
    turn = _CURRENT_TURN.get()
    if turn is None or turn.outcome is None:
        return
    with turn.lock:
        allowed = [u for u in urls if u in turn.allowed_urls]
        turn.used_urls = tuple(dict.fromkeys([*turn.used_urls, *allowed]))
        if turn.outcome.succeeded:
            turn.final_state = (
                WebState(ResultStatus.SUCCESS)
                if turn.used_urls
                else WebState(ResultStatus.ERROR, ErrorType.FETCH_FAILED)
            )


# ---------------------------------------------------------------------------
# User-facing text (categories only, never values)
# ---------------------------------------------------------------------------


def _category_text(categories: tuple[str, ...]) -> str:
    labels = [CATEGORY_LABELS.get(c, "sensitive material") for c in categories] or ["sensitive material"]
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " and " + labels[-1]


def blocked_notice(decision: WebDecision) -> str:
    """Deterministic reply for an explicit web request that was not performed."""
    if decision.error_type is ErrorType.EGRESS_BLOCKED_SENSITIVE:
        return (
            "I can't search the web from that message because it contains "
            f"{_category_text(decision.categories)}. I didn't send anything. "
            "Remove it and ask again with just what you want searched."
        )
    if decision.diagnostic == DIAG_QUERY_UNBUILDABLE:
        return (
            "I didn't search the web because I couldn't tell exactly what to look up "
            "from this message. What should I search for? Put it in one short line, "
            "for example: search the web for Python 3.13 release notes."
        )
    if decision.diagnostic == DIAG_OFFLINE:
        return (
            "Web access is off because offline mode is on (ZOE_OFFLINE=1), so I didn't "
            "search. This answer is from my own knowledge and may be out of date."
        )
    return ""


def web_outcome_notice() -> str:
    """Leading line describing what happened on an authorized web turn."""
    decision = current_decision()
    state = current_web_state()
    query = decision.query or ""
    if state.status is ResultStatus.SUCCESS:
        return f"Searched the web for: `{query}`"
    if state.error_type is ErrorType.NO_RESULTS:
        return (
            f"I searched the web for `{query}` and found no results, so this answer is from "
            "my own knowledge and may be out of date."
        )
    if state.error_type is ErrorType.FETCH_FAILED:
        return (
            f"I searched the web for `{query}` but couldn't read any of the result pages, "
            "so this answer is from my own knowledge and may be out of date."
        )
    if state.detail == DIAG_OFFLINE:
        return blocked_notice(WebDecision(ErrorType.NETWORK_UNAVAILABLE, diagnostic=DIAG_OFFLINE))
    if state.error_type is ErrorType.EGRESS_BLOCKED_SENSITIVE:
        return (
            "I didn't search the web because the request contained sensitive material, "
            "so this answer is from my own knowledge and may be out of date."
        )
    return FALLBACK_COULD_NOT_SEARCH


def decorate_web_reply(reply: str) -> str:
    """Prefix the outcome line and append provenance from this turn's real results."""
    notice = web_outcome_notice()
    body = f"{notice}\n\n{reply}".strip()
    if current_web_state().status is ResultStatus.SUCCESS:
        sources = current_used_sources()
        if sources:
            lines = ["Sources (web search results, untrusted external content):"]
            lines.extend(f"{i}. {title} — {url}" for i, (title, url) in enumerate(sources, 1))
            body = f"{body}\n\n" + "\n".join(lines)
    return body
