"""Export Sprint 23 curated JSONL datasets.

Usage (from repo root):
  python -m training.data.curation.export_sprint23

Does NOT train, download models, or modify Zoe runtime.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from training.data.curation import write_jsonl  # noqa: E402
from training.data.curation.bank_corrections import examples as correction_examples  # noqa: E402
from training.data.curation.bank_expand import examples as expand_examples  # noqa: E402
from training.data.curation.bank_extra import examples as extra_examples  # noqa: E402
from training.data.curation.bank_held_out import examples as held_out_examples  # noqa: E402
from training.data.curation.bank_personality import examples as personality_examples  # noqa: E402
from training.data.curation.bank_systems import examples as systems_examples  # noqa: E402
from training.data.curation.bank_technical import examples as technical_examples  # noqa: E402
from training.schema.validate import validate_paths  # noqa: E402

DATA = _REPO / "training" / "data"


def _dedupe_by_id(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        eid = str(row.get("id", ""))
        if not eid or eid in seen:
            continue
        seen.add(eid)
        out.append(row)
    return out


def _exclude_held_out_overlap(train_rows: list[dict], held_rows: list[dict]) -> list[dict]:
    held_users = {
        m["content"].strip().lower()
        for r in held_rows
        for m in r.get("messages", [])
        if m.get("role") == "user"
    }
    cleaned: list[dict] = []
    for row in train_rows:
        users = [
            m["content"].strip().lower()
            for m in row.get("messages", [])
            if m.get("role") == "user"
        ]
        if any(u in held_users for u in users):
            continue
        cleaned.append(row)
    return cleaned


def _stats(rows: list[dict]) -> dict:
    cats: Counter[str] = Counter()
    modes: Counter[str] = Counter()
    for row in rows:
        meta = row.get("metadata") or {}
        cats[str(meta.get("category", "?"))] += 1
        modes[str(meta.get("personality_mode", "?"))] += 1
    return {"n": len(rows), "categories": dict(cats), "personality_modes": dict(modes)}


def main() -> int:
    train_like = _dedupe_by_id(
        personality_examples()
        + technical_examples()
        + systems_examples()
        + expand_examples()
        + extra_examples()
    )
    held = _dedupe_by_id(held_out_examples())
    train_like = _exclude_held_out_overlap(train_like, held)
    corrections = _dedupe_by_id(correction_examples())

    # Historical seeds remain in training/data/seeds/ as format exemplars.
    # They are not auto-merged here (avoids near-duplicates with Sprint 23 banks).

    paths = {
        "clean": DATA / "clean" / "sft_sprint23.jsonl",
        "held_out": DATA / "held_out_eval" / "eval_sprint23.jsonl",
        "corrections": DATA / "corrections" / "corrections_sprint23.jsonl",
        "manifest": DATA / "clean" / "sprint23_manifest.json",
    }

    n_clean = write_jsonl(paths["clean"], train_like)
    n_held = write_jsonl(paths["held_out"], held)
    n_corr = write_jsonl(paths["corrections"], corrections)

    # Also refresh clean seed copy pointer file list via manifest only
    report = validate_paths([paths["clean"]], kind="sft")
    held_report = validate_paths([paths["held_out"]], kind="sft")
    corr_report = validate_paths([paths["corrections"]], kind="correction")

    manifest = {
        "sprint": 23,
        "trained": False,
        "counts": {
            "sft_clean": n_clean,
            "held_out_eval": n_held,
            "corrections": n_corr,
        },
        "sft_stats": _stats(train_like),
        "held_out_stats": _stats(held),
        "validation": {
            "sft_ok": report.ok,
            "sft_summary": report.summary(),
            "sft_errors": len(report.errors),
            "held_out_ok": held_report.ok,
            "held_out_summary": held_report.summary(),
            "corrections_ok": corr_report.ok,
            "corrections_summary": corr_report.summary(),
        },
        "notes": [
            "held_out must never be mixed into train",
            "metadata must never be fed to the model",
            "no adapter has been trained",
        ],
    }
    paths["manifest"].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(manifest["counts"], indent=2))
    print("validation:", manifest["validation"])
    print("wrote:", {k: str(v) for k, v in paths.items()})
    if not (report.ok and held_report.ok and corr_report.ok):
        for issue in report.errors[:10] + held_report.errors[:10] + corr_report.errors[:10]:
            print(f"ERROR {issue.path}:{issue.line} [{issue.code}] {issue.message}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
