"""Selective ingestion interfaces for real Zoe artifacts.

Nothing here auto-converts full history into training data.
Callers must choose specific records; privacy scan is mandatory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

from training.schema.privacy import PrivacyResult, scan_text


@dataclass
class IngestCandidate:
    source: str
    source_path: str
    raw_text: str
    suggested_category: str = "general_conversation"
    privacy: PrivacyResult | None = None
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_history_summary_candidates(
    summary_path: Path,
    *,
    max_items: int = 50,
) -> Iterator[IngestCandidate]:
    """Yield candidates from conversation summary JSON if present.

    Does not write training files. Operator must curate deliberately.
    """
    if not summary_path.exists():
        return
    data = _read_json(summary_path)
    # Support list or dict-with-items shapes without assuming production schema stability.
    items: Iterable[Any]
    if isinstance(data, list):
        items = data[:max_items]
    elif isinstance(data, dict):
        maybe = data.get("summaries") or data.get("items") or data.get("entries") or []
        items = list(maybe)[:max_items]
    else:
        return

    for idx, item in enumerate(items):
        if isinstance(item, str):
            text = item
        elif isinstance(item, dict):
            text = str(
                item.get("summary")
                or item.get("text")
                or item.get("content")
                or json.dumps(item, ensure_ascii=False)
            )
        else:
            continue
        privacy = scan_text(text)
        yield IngestCandidate(
            source="history_summary",
            source_path=str(summary_path),
            raw_text=text,
            suggested_category="general_conversation",
            privacy=privacy,
            notes=f"index={idx}; not auto-accepted",
        )


def iter_telemetry_event_candidates(
    telemetry_path: Path,
    *,
    max_lines: int = 100,
) -> Iterator[IngestCandidate]:
    """Scan telemetry JSONL for *structural* patterns only — not default training text.

    Most telemetry should never become SFT text. This surfaces candidates for
    error_handling / tool_routing review when events look useful.
    """
    if not telemetry_path.exists():
        return
    count = 0
    with telemetry_path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if count >= max_lines:
                break
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            # Prefer failure-like events for correction inspiration
            blob = json.dumps(event, ensure_ascii=False)
            lower = blob.lower()
            if not any(k in lower for k in ("error", "fail", "exception", "timeout")):
                continue
            privacy = scan_text(blob)
            count += 1
            yield IngestCandidate(
                source="telemetry",
                source_path=f"{telemetry_path}:{line_no}",
                raw_text=blob,
                suggested_category="error_handling",
                privacy=privacy,
                notes="telemetry candidate for human redesign — do not train on raw logs",
            )


def write_review_queue(candidates: Iterable[IngestCandidate], out_path: Path) -> int:
    """Write a human review queue JSONL (still not training data)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as handle:
        for cand in candidates:
            if cand.privacy is None:
                cand.privacy = scan_text(cand.raw_text)
            row = {
                "source": cand.source,
                "source_path": cand.source_path,
                "suggested_category": cand.suggested_category,
                "privacy_ok": cand.privacy.ok,
                "privacy_reasons": cand.privacy.reasons,
                "notes": cand.notes,
                "raw_text": cand.raw_text,
                "review_status": "pending",
                "extra": cand.extra,
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


KNOWN_LOCAL_SOURCES: dict[str, str] = {
    "history_summary": "data/history/summary.json",
    "telemetry": "data/telemetry/runtime.jsonl",
    "docs_personality_legacy": "docs/personality.md",
    "docs_personality_canonical": "docs/ZOE_PERSONALITY.md",
    "regression_tests": "tests/",
}
