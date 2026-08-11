"""Privacy filters for candidate training data from real Zoe sources."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Conservative patterns — reject or redact before any human review acceptance.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|secret|password|token|authorization)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[a-z0-9\-._~+/]+=*"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}\b")


@dataclass
class PrivacyResult:
    ok: bool
    reasons: list[str]
    redacted_text: str | None = None


def scan_text(text: str) -> PrivacyResult:
    reasons: list[str] = []
    if not text or not text.strip():
        return PrivacyResult(ok=False, reasons=["empty_text"])

    for pat in _SECRET_PATTERNS:
        if pat.search(text):
            reasons.append("possible_secret")
            break

    if _EMAIL.search(text):
        reasons.append("email_address")
    if _PHONE.search(text) and len(re.sub(r"\D", "", text)) >= 10:
        # soft signal — many code snippets have numbers; flag for review
        reasons.append("possible_phone")

    # Absolute reject for clear secrets; emails/phones → not ok until redacted/reviewed
    hard = "possible_secret" in reasons
    soft = any(r in reasons for r in ("email_address", "possible_phone"))
    ok = not hard and not soft
    return PrivacyResult(ok=ok, reasons=reasons, redacted_text=None)


def redact_basic(text: str) -> str:
    """Best-effort redaction for review drafts — not a guarantee."""
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED_SECRET]", out)
    out = _EMAIL.sub("[REDACTED_EMAIL]", out)
    return out
