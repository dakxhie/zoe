"""Content secret detection and redaction for Zoe filesystem tools (Phase B1).

Rules (ZOE_PHASE_A1_DESIGN.md, B1 content scanning):

- A private-key block anywhere in a file blocks the whole file.
- Any other high-confidence secret hit redacts the whole matching line.
- Callers report only a redaction count; secret values are never returned,
  logged, or included in error messages.

The conservative patterns in ``training/schema/privacy.py`` are reused (not
moved). Its broad ``key=value`` pattern is only treated as a hit when the
assigned value looks like a literal secret, so ordinary source lines such as
``token = tokenizer(text)`` or ``password: str`` are not redacted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from training.schema.privacy import scan_text as _privacy_scan_text

REDACTED_LINE = "[REDACTED: line contained a possible secret]"

PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----"
)

# High-confidence token shapes. Each match redacts the line it appears on.
_HIGH_CONFIDENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|ANPA|ANVA|AIPA)[A-Z0-9]{16}\b"),  # AWS key id
    re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),  # GitHub tokens
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b"),
    re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),  # Slack tokens
    re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]+"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),  # Google API key
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),  # JWT
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{20,}=*"),
    re.compile(r"(?i)\bauthorization\s*[:=]\s*['\"]?basic\s+[A-Za-z0-9+/]{8,}=*"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@"),  # credentials in URL
)

_ASSIGNMENT = re.compile(
    r"(?i)(?:api[_-]?key|apikey|secret(?:[_-]?key)?|client[_-]?secret|passw(?:or)?d|pwd|"
    r"access[_-]?token|auth[_-]?token|refresh[_-]?token|token|authorization)"
    r"['\"]?\s*[:=]\s*(?P<value>.+)$"
)
_PLACEHOLDER_VALUES = frozenset(
    {
        "", "none", "null", "nil", "true", "false", "str", "int", "bytes", "optional",
        "changeme", "change_me", "placeholder", "redacted", "example", "xxx", "xxxx",
        "your_key_here", "your-api-key", "todo", "tbd", "...",
    }
)
_CODE_HINT = re.compile(r"[()\[\]{}]|\b(?:os\.environ|getenv|settings|config|self|cls)\b")


@dataclass(frozen=True)
class ScanResult:
    """Outcome of scanning text before it leaves a filesystem tool."""

    blocked: bool
    text: str
    redacted_lines: int


def _literal_secret_value(raw: str) -> bool:
    """Return True when an assignment value looks like a literal secret."""
    value = raw.strip().rstrip(",;").strip()
    if not value:
        return False
    quoted = value[0] in "'\"" and len(value) >= 2
    if quoted:
        inner = value[1:].split(value[0], 1)[0].strip()
    else:
        if _CODE_HINT.search(value) or " " in value:
            return False
        inner = value
    lowered = inner.lower()
    if lowered in _PLACEHOLDER_VALUES:
        return False
    if lowered.startswith(("<", "${", "$", "%", "your", "xxx", "***", "example")):
        return False
    if set(inner) <= {"*", "x", "X", "-", "_", "."}:
        return False
    return len(inner) >= 6


def line_has_secret(line: str) -> bool:
    """Return True when one line contains a high-confidence secret."""
    if PRIVATE_KEY_BLOCK.search(line):
        return True
    if any(pattern.search(line) for pattern in _HIGH_CONFIDENCE_PATTERNS):
        return True
    match = _ASSIGNMENT.search(line)
    if match:
        return _literal_secret_value(match.group("value"))
    # Shared training privacy filter (reused, not moved) catches remaining shapes
    # such as bearer / sk- tokens; its generic assignment rule is handled above.
    return "possible_secret" in _privacy_scan_text(line).reasons


def contains_private_key(text: str) -> bool:
    """Return True when text contains a private-key block header."""
    return bool(PRIVATE_KEY_BLOCK.search(text))


def scan_and_redact(text: str) -> ScanResult:
    """Block private keys and redact secret-bearing lines from text."""
    if contains_private_key(text):
        return ScanResult(blocked=True, text="", redacted_lines=0)
    redacted = 0
    out: list[str] = []
    for line in text.splitlines():
        if line_has_secret(line):
            out.append(REDACTED_LINE)
            redacted += 1
        else:
            out.append(line)
    return ScanResult(blocked=False, text="\n".join(out), redacted_lines=redacted)
