"""Export Sprint 25 expanded datasets WITHOUT overwriting Sprint 23 clean SFT.

Writes:
  training/data/clean/sft_tanglish_sprint25.jsonl
  training/data/clean/sft_coding_sprint25.jsonl
  training/data/clean/sft_sprint25_combined.jsonl  (sprint23 + new tracks)
  training/data/held_out_eval/eval_tanglish_sprint25.jsonl
  training/data/held_out_eval/eval_coding_sprint25.jsonl
  training/data/held_out_eval/eval_tanglish_coding_sprint25.jsonl
  training/data/held_out_eval/eval_tool_honesty_sprint25.jsonl
  training/data/held_out_eval/held_out_ids_sprint25.txt
  training/data/clean/sprint25_manifest.json

Does NOT train, download models, or modify production runtime.
Does NOT overwrite training/data/clean/sft_sprint23.jsonl.
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
from training.data.curation.coding.bank import examples as coding_examples  # noqa: E402
from training.data.curation.coding.held_out import (  # noqa: E402
    held_out_examples as coding_held_out,
)
from training.data.curation.coding.held_out import (  # noqa: E402
    tool_honesty_held_out,
)
from training.data.curation.tanglish.bank import examples as tanglish_examples  # noqa: E402
from training.data.curation.tanglish.bank import (  # noqa: E402
    held_out_examples as tanglish_held_out,
)
from training.data.curation.tanglish.bank import (  # noqa: E402
    mixed_coding_held_out,
)
from training.schema.validate import validate_paths  # noqa: E402
from training.scripts.guards import assert_train_not_held_out, user_contents  # noqa: E402

DATA = _REPO / "training" / "data"
S23_CLEAN = DATA / "clean" / "sft_sprint23.jsonl"


def _balanced_subset(
    legacy: list[dict],
    tanglish: list[dict],
    coding: list[dict],
    *,
    seed: int = 25,
) -> list[dict]:
    """Build recommended composition without inventing duplicates.

    Target roughly: ~55% legacy, ~18% Tanglish, ~27% coding on a ~620-row set.
    Full track JSONL files remain available for later experiments.
    """
    import random

    rng = random.Random(seed)
    # Keep all legacy (identity + prior coverage).
    n_tl = min(len(tanglish), 115)
    n_cd = min(len(coding), 170)
    tl_pick = rng.sample(tanglish, n_tl) if n_tl else []
    cd_pick = rng.sample(coding, n_cd) if n_cd else []
    return _dedupe_by_id(list(legacy) + tl_pick + cd_pick)


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line:
            rows.append(json.loads(line))
    return rows


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


def _exclude_held_users(train_rows: list[dict], held_rows: list[dict]) -> list[dict]:
    held_users = {
        u
        for r in held_rows
        for u in user_contents(r)
    }
    cleaned: list[dict] = []
    for row in train_rows:
        users = user_contents(row)
        if any(u in held_users for u in users):
            continue
        cleaned.append(row)
    return cleaned


def _stats(rows: list[dict]) -> dict:
    cats: Counter[str] = Counter()
    modes: Counter[str] = Counter()
    tracks: Counter[str] = Counter()
    for row in rows:
        meta = row.get("metadata") or {}
        cats[str(meta.get("category", "?"))] += 1
        modes[str(meta.get("personality_mode", "?"))] += 1
        extra = meta.get("extra") or {}
        tracks[str(extra.get("track", "legacy_s23"))] += 1
    n = len(rows) or 1
    return {
        "n": len(rows),
        "categories": dict(cats),
        "personality_modes": dict(modes),
        "personality_mode_pct": {k: round(100 * v / n, 2) for k, v in modes.items()},
        "tracks": dict(tracks),
        "track_pct": {k: round(100 * v / n, 2) for k, v in tracks.items()},
    }


def main() -> int:
    if not S23_CLEAN.exists():
        print(f"ERROR: missing preserved Sprint 23 dataset: {S23_CLEAN}")
        return 1

    s23 = _read_jsonl(S23_CLEAN)
    print(f"Preserved Sprint 23 clean rows: {len(s23)} (will not overwrite file)")

    tl = _dedupe_by_id(tanglish_examples())
    cd = _dedupe_by_id(coding_examples())
    held = _dedupe_by_id(
        tanglish_held_out() + mixed_coding_held_out() + coding_held_out() + tool_honesty_held_out()
    )

    tl = _exclude_held_users(tl, held)
    cd = _exclude_held_users(cd, held)

    # Mark legacy track for composition stats
    for row in s23:
        meta = row.setdefault("metadata", {})
        extra = meta.setdefault("extra", {})
        extra.setdefault("track", "legacy_s23")

    combined = _dedupe_by_id(s23 + tl + cd)
    combined = _exclude_held_users(combined, held)
    balanced = _exclude_held_users(_balanced_subset(s23, tl, cd), held)

    paths = {
        "tanglish": DATA / "clean" / "sft_tanglish_sprint25.jsonl",
        "coding": DATA / "clean" / "sft_coding_sprint25.jsonl",
        "combined": DATA / "clean" / "sft_sprint25_combined.jsonl",
        "balanced": DATA / "clean" / "sft_sprint25_balanced.jsonl",
        "held_tl": DATA / "held_out_eval" / "eval_tanglish_sprint25.jsonl",
        "held_cd": DATA / "held_out_eval" / "eval_coding_sprint25.jsonl",
        "held_mix": DATA / "held_out_eval" / "eval_tanglish_coding_sprint25.jsonl",
        "held_tool": DATA / "held_out_eval" / "eval_tool_honesty_sprint25.jsonl",
        "held_ids": DATA / "held_out_eval" / "held_out_ids_sprint25.txt",
        "manifest": DATA / "clean" / "sprint25_manifest.json",
    }

    write_jsonl(paths["tanglish"], tl)
    write_jsonl(paths["coding"], cd)
    write_jsonl(paths["combined"], combined)
    write_jsonl(paths["balanced"], balanced)
    write_jsonl(paths["held_tl"], tanglish_held_out())
    write_jsonl(paths["held_cd"], coding_held_out())
    write_jsonl(paths["held_mix"], mixed_coding_held_out())
    write_jsonl(paths["held_tool"], tool_honesty_held_out())

    held_ids = sorted({str(r.get("id", "")) for r in held if r.get("id")})
    paths["held_ids"].write_text("\n".join(held_ids) + "\n", encoding="utf-8")

    # Leakage guards vs combined train candidate
    leak_errs = assert_train_not_held_out(paths["combined"], paths["held_tl"])
    leak_errs += assert_train_not_held_out(paths["combined"], paths["held_cd"])
    leak_errs += assert_train_not_held_out(paths["combined"], paths["held_mix"])
    leak_errs += assert_train_not_held_out(paths["combined"], paths["held_tool"])
    leak_errs += assert_train_not_held_out(paths["balanced"], paths["held_tl"])
    leak_errs += assert_train_not_held_out(paths["balanced"], paths["held_cd"])
    leak_errs += assert_train_not_held_out(paths["balanced"], paths["held_mix"])
    leak_errs += assert_train_not_held_out(paths["balanced"], paths["held_tool"])
    # also protect original sprint23 held-out
    s23_held = DATA / "held_out_eval" / "eval_sprint23.jsonl"
    if s23_held.exists():
        leak_errs += assert_train_not_held_out(paths["combined"], s23_held)
        leak_errs += assert_train_not_held_out(paths["balanced"], s23_held)
        leak_errs += assert_train_not_held_out(paths["tanglish"], s23_held)
        leak_errs += assert_train_not_held_out(paths["coding"], s23_held)

    reports = {
        "tanglish": validate_paths([paths["tanglish"]], kind="sft"),
        "coding": validate_paths([paths["coding"]], kind="sft"),
        "combined": validate_paths([paths["combined"]], kind="sft"),
        "balanced": validate_paths([paths["balanced"]], kind="sft"),
        "held_tl": validate_paths([paths["held_tl"]], kind="sft"),
        "held_cd": validate_paths([paths["held_cd"]], kind="sft"),
        "held_mix": validate_paths([paths["held_mix"]], kind="sft"),
        "held_tool": validate_paths([paths["held_tool"]], kind="sft"),
    }

    nb = len(balanced) or 1
    bal_tracks = Counter(
        ((r.get("metadata") or {}).get("extra") or {}).get("track", "legacy_s23")
        for r in balanced
    )
    composition = {
        "legacy_s23": len(s23),
        "tanglish_full_bank": len(tl),
        "coding_full_bank": len(cd),
        "combined_all": len(combined),
        "balanced_for_first_ft": len(balanced),
        "balanced_tracks": dict(bal_tracks),
        "balanced_pct": {k: round(100 * v / nb, 2) for k, v in bal_tracks.items()},
        "recommended_training_file": "training/data/clean/sft_sprint25_balanced.jsonl",
        "note": (
            "Full banks preserved separately. Balanced file samples Tanglish/coding "
            "so legacy Zoe identity remains majority for the first Colab run."
        ),
    }

    manifest = {
        "sprint": 25,
        "trained": False,
        "preserved_sprint23_path": str(S23_CLEAN),
        "preserved_sprint23_count": len(s23),
        "counts": {
            "tanglish_train": len(tl),
            "coding_train": len(cd),
            "combined_clean": len(combined),
            "balanced_clean": len(balanced),
            "held_tanglish": len(tanglish_held_out()),
            "held_coding": len(coding_held_out()),
            "held_tanglish_coding": len(mixed_coding_held_out()),
            "held_tool_honesty": len(tool_honesty_held_out()),
            "held_total_new": len(held),
        },
        "composition": composition,
        "stats": {
            "tanglish": _stats(tl),
            "coding": _stats(cd),
            "combined": _stats(combined),
            "balanced": _stats(balanced),
        },
        "validation": {
            name: {"ok": rep.ok, "summary": rep.summary(), "errors": len(rep.errors)}
            for name, rep in reports.items()
        },
        "leakage_errors": leak_errs[:50],
        "leakage_ok": not leak_errs,
        "notes": [
            "sft_sprint23.jsonl was not overwritten",
            "external Tanglish corpora were audited but not bulk-ingested",
            "held-out sets must never be mixed into train",
            "use sft_sprint25_balanced.jsonl for first Colab QLoRA",
            "no adapter has been trained",
        ],
    }
    paths["manifest"].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(manifest["counts"], indent=2))
    print("composition:", json.dumps(composition, indent=2))
    print("leakage_ok:", manifest["leakage_ok"], "errors:", len(leak_errs))
    for name, rep in reports.items():
        print(f"validate {name}: {rep.summary()} ok={rep.ok}")
        if not rep.ok:
            for err in rep.errors[:5]:
                print(f"  ERROR {err.code}: {err.message}")
    return 0 if manifest["leakage_ok"] and all(r.ok for r in reports.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
