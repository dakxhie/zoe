"""Export Sprint 26 quality-focused balanced dataset.

Preserves:
  training/data/clean/sft_sprint23.jsonl
  training/data/clean/sft_sprint25_balanced.jsonl

Writes:
  training/data/clean/sft_sprint26_balanced.jsonl
  training/data/held_out_eval/eval_sprint26.jsonl
  training/data/corrections/corrections_sprint26.jsonl
  training/data/held_out_eval/held_out_ids_sprint26.txt
  training/data/clean/sprint26_manifest.json

No training / no weight downloads / no runtime changes.
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from training.data.curation import write_jsonl  # noqa: E402
from training.data.curation.bank_sprint26 import (  # noqa: E402
    correction_examples,
    examples as sprint26_gap_examples,
)
from training.data.curation.bank_sprint26_held_out import examples as held_out_examples  # noqa: E402
from training.schema.validate import validate_paths  # noqa: E402
from training.scripts.guards import assert_train_not_held_out, user_contents  # noqa: E402

DATA = _REPO / "training" / "data"
S23 = DATA / "clean" / "sft_sprint23.jsonl"
S25_BAL = DATA / "clean" / "sft_sprint25_balanced.jsonl"
S25_TL = DATA / "clean" / "sft_tanglish_sprint25.jsonl"
S25_CD = DATA / "clean" / "sft_coding_sprint25.jsonl"


def _read(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _asst(row: dict) -> str:
    for m in row.get("messages") or []:
        if m.get("role") == "assistant":
            return str(m.get("content", "")).strip()
    return ""


def _dedupe_id(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        eid = str(row.get("id", ""))
        if not eid or eid in seen:
            continue
        seen.add(eid)
        out.append(row)
    return out


def _dedupe_assistant(rows: list[dict]) -> list[dict]:
    """Keep first occurrence of each exact assistant text (drops template clones)."""
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        key = _asst(row).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _exclude_held(rows: list[dict], held: list[dict]) -> list[dict]:
    held_users = {u for r in held for u in user_contents(r)}
    held_ids = {str(r.get("id", "")) for r in held}
    out = []
    for row in rows:
        if str(row.get("id", "")) in held_ids:
            continue
        if any(u in held_users for u in user_contents(row)):
            continue
        out.append(row)
    return out


def _pick_diverse_tanglish(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    """Prefer non-coding Tanglish first, then fill with coding Tanglish."""
    rows = _dedupe_assistant(_dedupe_id(rows))
    non_code = [r for r in rows if (r.get("metadata") or {}).get("category") != "coding"]
    code = [r for r in rows if (r.get("metadata") or {}).get("category") == "coding"]
    rng.shuffle(non_code)
    rng.shuffle(code)
    # Aim ~55% non-coding within Tanglish slice when possible
    n_non = min(len(non_code), max(int(n * 0.55), 40))
    n_code = min(len(code), n - n_non)
    # if non_code short, fill from code
    picked = non_code[:n_non] + code[:n_code]
    if len(picked) < n:
        rest = [r for r in code[n_code:] + non_code[n_non:] if r not in picked]
        picked.extend(rest[: n - len(picked)])
    return picked[:n]


def _pick_unique_coding(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    rows = _dedupe_assistant(_dedupe_id(rows))
    # Prefer longer, more specific assistants (debug/review style) slightly
    rows = sorted(rows, key=lambda r: len(_asst(r)), reverse=True)
    head = rows[: max(n * 2, n)]
    rng.shuffle(head)
    return head[:n]


def _stats(rows: list[dict]) -> dict:
    modes = Counter((r.get("metadata") or {}).get("personality_mode") for r in rows)
    cats = Counter((r.get("metadata") or {}).get("category") for r in rows)
    tracks = Counter(
        ((r.get("metadata") or {}).get("extra") or {}).get("track", "legacy_or_unmarked")
        for r in rows
    )
    sources = Counter((r.get("metadata") or {}).get("source") for r in rows)
    n = len(rows) or 1
    return {
        "n": len(rows),
        "personality_modes": dict(modes),
        "personality_mode_pct": {k: round(100 * v / n, 2) for k, v in modes.items()},
        "categories": dict(cats),
        "tracks": dict(tracks),
        "track_pct": {k: round(100 * v / n, 2) for k, v in tracks.items()},
        "sources": dict(sources),
    }


def main() -> int:
    if not S23.exists() or not S25_BAL.exists():
        print("ERROR: Sprint 23/25 balanced files must exist and remain untouched.")
        return 1

    rng = random.Random(26)
    s23 = _read(S23)
    for row in s23:
        meta = row.setdefault("metadata", {})
        extra = meta.setdefault("extra", {})
        extra.setdefault("track", "legacy_s23")

    held = _dedupe_id(held_out_examples())
    gap = _dedupe_id(sprint26_gap_examples())
    corr = _dedupe_id(correction_examples())

    tl_full = _read(S25_TL) if S25_TL.exists() else []
    cd_full = _read(S25_CD) if S25_CD.exists() else []

    # Quality-selected slices from Sprint 25 banks (deduped assistants).
    tl_pick = _pick_diverse_tanglish(tl_full, 150, rng)
    cd_pick = _pick_unique_coding(cd_full, 200, rng)

    for row in tl_pick:
        (row.setdefault("metadata", {}).setdefault("extra", {})).setdefault("track", "tanglish")
    for row in cd_pick:
        (row.setdefault("metadata", {}).setdefault("extra", {})).setdefault("track", "elite_coding")
    for row in gap:
        extra = row.setdefault("metadata", {}).setdefault("extra", {})
        if "track" not in extra:
            src = str((row.get("metadata") or {}).get("source", ""))
            if "tanglish" in src or str(row.get("id", "")).startswith("s26_tl_"):
                extra["track"] = "tanglish"
            elif str(row.get("id", "")).startswith("s26_tool_"):
                extra["track"] = "tool_honesty"
            elif str(row.get("id", "")).startswith("s26_pers_"):
                extra["track"] = "personality"
            else:
                extra["track"] = "elite_coding"

    balanced = _dedupe_id(s23 + tl_pick + cd_pick + gap)
    balanced = _exclude_held(balanced, held)
    # Also protect prior held-outs
    prior_held_files = [
        DATA / "held_out_eval" / "eval_sprint23.jsonl",
        DATA / "held_out_eval" / "eval_tanglish_sprint25.jsonl",
        DATA / "held_out_eval" / "eval_coding_sprint25.jsonl",
        DATA / "held_out_eval" / "eval_tanglish_coding_sprint25.jsonl",
        DATA / "held_out_eval" / "eval_tool_honesty_sprint25.jsonl",
    ]
    prior_held: list[dict] = []
    for p in prior_held_files:
        if p.exists():
            prior_held.extend(_read(p))
    balanced = _exclude_held(balanced, prior_held)

    paths = {
        "balanced": DATA / "clean" / "sft_sprint26_balanced.jsonl",
        "held": DATA / "held_out_eval" / "eval_sprint26.jsonl",
        "corr": DATA / "corrections" / "corrections_sprint26.jsonl",
        "ids": DATA / "held_out_eval" / "held_out_ids_sprint26.txt",
        "manifest": DATA / "clean" / "sprint26_manifest.json",
    }

    write_jsonl(paths["balanced"], balanced)
    write_jsonl(paths["held"], held)
    write_jsonl(paths["corr"], corr)
    paths["ids"].write_text(
        "\n".join(sorted(str(r.get("id", "")) for r in held if r.get("id"))) + "\n",
        encoding="utf-8",
    )

    leak = assert_train_not_held_out(paths["balanced"], paths["held"])
    for p in prior_held_files:
        if p.exists():
            leak += assert_train_not_held_out(paths["balanced"], p)

    reports = {
        "balanced": validate_paths([paths["balanced"]], kind="sft"),
        "held": validate_paths([paths["held"]], kind="sft"),
        "corr": validate_paths([paths["corr"]], kind="correction"),
    }

    # Verify Sprint 25 balanced untouched size
    s25_n = len(_read(S25_BAL))
    s23_n = len(s23)

    asst_dups = sum(
        1 for a, n in Counter(_asst(r).lower() for r in balanced).items() if a and n > 1
    )

    manifest = {
        "sprint": 26,
        "trained": False,
        "preserved": {
            "sft_sprint23.jsonl": s23_n,
            "sft_sprint25_balanced.jsonl": s25_n,
        },
        "counts": {
            "sprint26_balanced": len(balanced),
            "held_out": len(held),
            "corrections": len(corr),
            "from_s23": s23_n,
            "from_s25_tanglish_deduped": len(tl_pick),
            "from_s25_coding_deduped": len(cd_pick),
            "sprint26_gap_fill": len(gap),
        },
        "stats": _stats(balanced),
        "held_stats": _stats(held),
        "quality": {
            "exact_assistant_dup_groups_in_balanced": asst_dups,
            "coding_bank_assistant_dedupe_applied": True,
            "tanglish_diversity_preference_non_coding": True,
        },
        "validation": {
            k: {"ok": r.ok, "summary": r.summary(), "errors": len(r.errors), "warnings": len(r.warnings)}
            for k, r in reports.items()
        },
        "leakage_ok": not leak,
        "leakage_errors": leak[:40],
        "notes": [
            "Sprint 23 and Sprint 25 balanced files were not overwritten",
            "Sprint 26 prefers quality: deduped coding assistants, diversified Tanglish",
            "External Tanglish corpora not bulk-ingested",
            "Use sft_sprint26_balanced.jsonl for the final Colab QLoRA prepare step",
        ],
    }
    paths["manifest"].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(manifest["counts"], indent=2))
    print("tracks", manifest["stats"]["track_pct"])
    print("modes", manifest["stats"]["personality_mode_pct"])
    print("leakage_ok", manifest["leakage_ok"], "asst_dup_groups", asst_dups)
    for k, r in reports.items():
        print(f"validate {k}: {r.summary()} ok={r.ok}")
        if not r.ok:
            for e in r.errors[:5]:
                print(" ", e.code, e.message)
    return 0 if manifest["leakage_ok"] and all(r.ok for r in reports.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
