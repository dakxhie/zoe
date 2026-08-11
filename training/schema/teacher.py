"""Teacher / synthetic example pipeline stages.

Never blindly dump teacher outputs into training. Stages:

1. generate → 2. validate → 3. dedupe → 4. quality_score → 5. review → 6. accept/reject
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from training.schema.validate import validate_sft_record


ReviewDecision = str  # pending | accepted | rejected


@dataclass
class TeacherRecord:
    id: str
    draft: dict[str, Any]
    stage: str = "generated"
    quality_score: float | None = None
    review_status: ReviewDecision = "pending"
    review_notes: str = ""
    duplicate_of: str | None = None


@dataclass
class TeacherPipelineState:
    records: list[TeacherRecord] = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "id": r.id,
                "draft": r.draft,
                "stage": r.stage,
                "quality_score": r.quality_score,
                "review_status": r.review_status,
                "review_notes": r.review_notes,
                "duplicate_of": r.duplicate_of,
            }
            for r in self.records
        ]
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> TeacherPipelineState:
        data = json.loads(path.read_text(encoding="utf-8"))
        records = [
            TeacherRecord(
                id=str(row["id"]),
                draft=dict(row["draft"]),
                stage=str(row.get("stage", "generated")),
                quality_score=row.get("quality_score"),
                review_status=str(row.get("review_status", "pending")),
                review_notes=str(row.get("review_notes", "")),
                duplicate_of=row.get("duplicate_of"),
            )
            for row in data
        ]
        return cls(records=records)


def stage_validate(state: TeacherPipelineState) -> TeacherPipelineState:
    for rec in state.records:
        issues = validate_sft_record(rec.draft, path="<teacher>", line=0)
        errors = [i for i in issues if i.level == "error"]
        if errors:
            rec.stage = "validation_failed"
            rec.review_status = "rejected"
            rec.review_notes = "; ".join(i.message for i in errors)
        else:
            rec.stage = "validated"
    return state


def stage_dedupe(state: TeacherPipelineState) -> TeacherPipelineState:
    seen: dict[str, str] = {}
    for rec in state.records:
        messages = rec.draft.get("messages") or []
        user = " ".join(
            m.get("content", "")
            for m in messages
            if isinstance(m, dict) and m.get("role") == "user"
        )
        asst = " ".join(
            m.get("content", "")
            for m in messages
            if isinstance(m, dict) and m.get("role") == "assistant"
        )
        digest = hashlib.sha256(f"{user}\n{asst}".strip().lower().encode()).hexdigest()
        if digest in seen:
            rec.stage = "duplicate"
            rec.duplicate_of = seen[digest]
            rec.review_status = "rejected"
            rec.review_notes = f"duplicate of {seen[digest]}"
        else:
            seen[digest] = rec.id
            if rec.stage == "validated":
                rec.stage = "deduped"
    return state


def default_quality_scorer(draft: dict[str, Any]) -> float:
    """Heuristic placeholder — human review still required."""
    messages = draft.get("messages") or []
    asst = " ".join(
        m.get("content", "")
        for m in messages
        if isinstance(m, dict) and m.get("role") == "assistant"
    )
    score = 0.5
    if 40 <= len(asst) <= 1200:
        score += 0.2
    if asst and not asst.lower().startswith("as an ai"):
        score += 0.1
    meta = draft.get("metadata") or {}
    if meta.get("category"):
        score += 0.1
    if meta.get("safety_sensitive") and meta.get("personality_mode") != "serious_no_humor":
        score -= 0.3
    return max(0.0, min(1.0, score))


def stage_quality_score(
    state: TeacherPipelineState,
    scorer: Callable[[dict[str, Any]], float] | None = None,
) -> TeacherPipelineState:
    scorer = scorer or default_quality_scorer
    for rec in state.records:
        if rec.review_status == "rejected":
            continue
        rec.quality_score = scorer(rec.draft)
        rec.stage = "scored"
        if rec.quality_score < 0.55:
            rec.review_notes = (rec.review_notes + " low_heuristic_score").strip()
    return state


def export_accepted(state: TeacherPipelineState, out_jsonl: Path) -> int:
    """Export only human-accepted records to a clean JSONL."""
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_jsonl.open("w", encoding="utf-8") as handle:
        for rec in state.records:
            if rec.review_status != "accepted":
                continue
            handle.write(json.dumps(rec.draft, ensure_ascii=False) + "\n")
            n += 1
    return n


REVIEW_QUEUE_FIELDS = (
    "id",
    "review_status",
    "review_notes",
    "quality_score",
    "stage",
    "draft",
)
