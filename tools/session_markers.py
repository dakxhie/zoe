"""Privacy-safe session markers for previously sensitive content (A.1 §6.4).

A.1 §6.4 blocks outbound web queries that contain "any substring that appeared
in a ``sensitive_path`` or redacted tool result this session". This module
implements that without a secret store:

- When a filesystem tool redacts a line, or denies a sensitive path, the
  sensitive value is normalized (the rules below) and every 4-character
  window (shingle) of it is reduced to a keyed fingerprint: HMAC-SHA256 with a
  random per-session key, truncated to 16 bytes. The raw value and its
  shingles are discarded immediately and never stored.
- The key exists only in this process's memory and is replaced on session
  reset, so fingerprints cannot be compared across sessions or reversed into
  the original text.
- At most ``MAX_FINGERPRINTS`` (50,000) fingerprints are held per session. If
  recording would exceed that, the store fails closed: every later web egress
  check in the session is blocked (``egress_blocked_sensitive``) until reset.
- Fingerprints and the key are never persisted, logged, sent anywhere, shown
  to the model, or included in user-facing text. Only counts are observable.

Normalization (unchanged from the accepted rules): a secret-bearing line keeps
only the part after its first ``key=`` / ``key:`` label; values are split on
characters outside ``[A-Za-z0-9_-./+~@]``; tokens shorter than
``MIN_TOKEN_CHARS`` and generic labels (``token``, ``password``, ...) are
dropped; a refused path is quote-stripped, uses ``/`` separators, and is
recorded as the whole path plus its final component.

Matching: an outgoing message or query is normalized the same way, shingled
the same way, and blocked when ANY of its shingle fingerprints was recorded.
This is a substring check (a recorded value inside a longer token still
matches) and deliberately over-blocks (fails closed): text that shares any
4-character window with a recorded value is blocked for the rest of the
session.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import threading
from typing import Iterable

logger = logging.getLogger(__name__)

MIN_TOKEN_CHARS = 6
SHINGLE_CHARS = 4
FINGERPRINT_BYTES = 16
MAX_FINGERPRINTS = 50_000
_TOKEN_SPLIT = re.compile(r"[^A-Za-z0-9_\-./+~@]+")
_ASSIGN_SPLIT = re.compile(r"[:=]")
# Generic words that commonly label a secret but are not the secret.
_STOP_TOKENS = frozenset(
    {
        "bearer", "basic", "token", "tokens", "secret", "secrets", "password", "passwd",
        "apikey", "api_key", "api-key", "access_token", "auth_token", "authorization",
        "export", "const", "string", "private", "public", "client_secret", "secret_key",
        "refresh_token", "redacted", "https", "http",
    }
)

CATEGORY_REDACTED = "previously_redacted_content"
CATEGORY_SENSITIVE_PATH = "previously_sensitive_path"
CATEGORY_CAPACITY = "session_marker_capacity_exceeded"


def _shingles(values: Iterable[str]) -> set[str]:
    """Every ``SHINGLE_CHARS``-character window of each normalized value."""
    out: set[str] = set()
    for value in values:
        if len(value) < SHINGLE_CHARS:
            continue
        out.update(value[i : i + SHINGLE_CHARS] for i in range(len(value) - SHINGLE_CHARS + 1))
    return out


class _SessionMarkers:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._key = secrets.token_bytes(32)
        self._fingerprints: dict[bytes, str] = {}
        self._overflowed = False

    def _fp(self, shingle: str) -> bytes:
        return hmac.new(self._key, shingle.encode("utf-8"), hashlib.sha256).digest()[:FINGERPRINT_BYTES]

    def add(self, values: set[str], category: str) -> int:
        """Fingerprint every shingle of ``values``; return how many were new."""
        shingles = _shingles(values)
        with self._lock:
            new = {fp for fp in (self._fp(s) for s in shingles) if fp not in self._fingerprints}
            if len(self._fingerprints) + len(new) > MAX_FINGERPRINTS:
                # Fail closed: the store can no longer represent everything
                # that was sensitive, so every later egress check is blocked.
                self._overflowed = True
                return 0
            for fp in new:
                self._fingerprints[fp] = category
            return len(new)

    def match(self, values: set[str]) -> tuple[str, ...]:
        with self._lock:
            if self._overflowed:
                return (CATEGORY_CAPACITY,)
            if not self._fingerprints:
                return ()
            found = {
                self._fingerprints[fp]
                for s in _shingles(values)
                if (fp := self._fp(s)) in self._fingerprints
            }
        return tuple(sorted(found))

    def reset(self) -> None:
        with self._lock:
            self._key = secrets.token_bytes(32)
            self._fingerprints.clear()
            self._overflowed = False

    def count(self) -> int:
        with self._lock:
            return len(self._fingerprints)

    def overflowed(self) -> bool:
        with self._lock:
            return self._overflowed

    def stored_values_for_tests(self) -> tuple[bytes, ...]:
        with self._lock:
            return tuple(self._fingerprints)


_MARKERS = _SessionMarkers()


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_SPLIT.split(text)
        if len(token) >= MIN_TOKEN_CHARS and token.lower() not in _STOP_TOKENS
    }


def _value_part(line: str) -> str:
    """The part of a secret-bearing line after its first ``key=`` / ``key:`` label."""
    parts = _ASSIGN_SPLIT.split(line, maxsplit=1)
    if len(parts) == 2 and re.fullmatch(r"\s*[\w.\-\"' ]{1,64}\s*", parts[0]):
        return parts[1]
    return line


def record_redacted_lines(lines: list[str]) -> None:
    """Fingerprint shingles of secret values from lines a tool redacted. Values are not kept."""
    values: set[str] = set()
    for line in lines:
        value = _value_part(line)
        values |= _tokens(value)
        stripped = value.strip().strip("\"'`,; ")
        if len(stripped) >= MIN_TOKEN_CHARS and " " not in stripped:
            values.add(stripped)
    added = _MARKERS.add(values, CATEGORY_REDACTED)
    if added:
        logger.debug("Session markers: %d new redacted-content fingerprint(s)", added)


def record_sensitive_path(path: str) -> None:
    """Fingerprint shingles of a path a tool refused as sensitive. The path is not kept."""
    normalized = path.strip().strip("\"'`").replace("\\", "/")
    if not normalized:
        return
    candidates = {normalized, normalized.rsplit("/", 1)[-1]} | _tokens(normalized)
    values = {c for c in candidates if len(c) >= MIN_TOKEN_CHARS and c.lower() not in _STOP_TOKENS}
    added = _MARKERS.add(values, CATEGORY_SENSITIVE_PATH)
    if added:
        logger.debug("Session markers: %d new sensitive-path fingerprint(s)", added)


def match_session_markers(text: str) -> tuple[str, ...]:
    """Return marker categories whose fingerprints occur in ``text`` (never values).

    After a capacity overflow every check returns ``CATEGORY_CAPACITY``.
    """
    if _MARKERS.overflowed():
        return (CATEGORY_CAPACITY,)
    if not text:
        return ()
    candidates = _tokens(text)
    for raw in re.split(r"\s+", text):
        cleaned = raw.strip().strip("\"'`,;.!?()[]{}<>").replace("\\", "/")
        if len(cleaned) >= MIN_TOKEN_CHARS:
            candidates.add(cleaned)
    return _MARKERS.match(candidates)


def reset_session_markers() -> None:
    """Discard every marker, clear the overflow state and rotate the key (session end)."""
    _MARKERS.reset()


def marker_count() -> int:
    """Number of fingerprints held (no values are available)."""
    return _MARKERS.count()


def markers_overflowed() -> bool:
    """True when the per-session fingerprint cap was exceeded (fail closed)."""
    return _MARKERS.overflowed()


def _stored_fingerprints_for_tests() -> tuple[bytes, ...]:
    return _MARKERS.stored_values_for_tests()
