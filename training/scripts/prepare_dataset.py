"""Prepare / split curated clean JSONL into train / validation.

Does not download models. Does not train.
Does not auto-ingest conversation history.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from training.schema.validate import validate_paths  # noqa: E402
from training.scripts.guards import assert_train_not_held_out, user_contents  # noqa: E402


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _held_out_blocklists(held_path: Path) -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    users: set[str] = set()
    if not held_path.exists():
        return ids, users
    files = [held_path] if held_path.is_file() else sorted(held_path.glob("*.jsonl"))
    for file_path in files:
        for row in _read_jsonl(file_path):
            eid = str(row.get("id", "")).strip()
            if eid:
                ids.add(eid)
            users.update(user_contents(row))
    return ids, users


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Split validated clean JSONL into train/validation (no training)."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=_REPO / "training" / "data" / "clean" / "sft_sprint23.jsonl",
        help="Clean SFT JSONL file or directory",
    )
    parser.add_argument("--train-out", type=Path, default=None)
    parser.add_argument("--val-out", type=Path, default=None)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--held-out",
        type=Path,
        default=_REPO / "training" / "data" / "held_out_eval" / "eval_sprint23.jsonl",
        help="Held-out JSONL used to block ids/user prompts from train/val",
    )
    parser.add_argument(
        "--held-out-ids",
        type=Path,
        default=_REPO / "training" / "data" / "held_out_eval" / "held_out_ids.txt",
        help="Written/read blocklist of held-out ids",
    )
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="Use Sprint 24/25 pilot output filenames (sft_pilot.jsonl)",
    )
    parser.add_argument(
        "--sprint25-balanced",
        action="store_true",
        help="Use Sprint 25 balanced clean SFT as input (Tanglish+coding blend).",
    )
    parser.add_argument(
        "--sprint26-balanced",
        action="store_true",
        help="Use Sprint 26 quality-balanced clean SFT as input (recommended).",
    )
    args = parser.parse_args(argv)

    if args.sprint26_balanced:
        args.input = _REPO / "training" / "data" / "clean" / "sft_sprint26_balanced.jsonl"
        # Canonical held-out for Sprint 26 FT — post-split assert must use this file.
        default_held = _REPO / "training" / "data" / "held_out_eval" / "eval_sprint23.jsonl"
        if args.held_out == default_held:
            args.held_out = (
                _REPO / "training" / "data" / "held_out_eval" / "eval_sprint26.jsonl"
            )
    elif args.sprint25_balanced and args.input == _REPO / "training" / "data" / "clean" / "sft_sprint23.jsonl":
        args.input = _REPO / "training" / "data" / "clean" / "sft_sprint25_balanced.jsonl"

    if args.train_out is None:
        name = "sft_pilot.jsonl" if args.pilot else "sft.jsonl"
        args.train_out = _REPO / "training" / "data" / "train" / name
    if args.val_out is None:
        name = "sft_pilot.jsonl" if args.pilot else "sft.jsonl"
        args.val_out = _REPO / "training" / "data" / "validation" / name

    report = validate_paths(
        [args.input] if args.input.is_file() else [args.input],
        kind="sft",
    )
    if not report.ok:
        print("Validation failed:", report.summary())
        for err in report.errors[:20]:
            print(f"  ERROR {err.path}:{err.line} [{err.code}] {err.message}")
        return 1

    files = [args.input] if args.input.is_file() else sorted(args.input.glob("*.jsonl"))
    if not args.input.is_file():
        preferred = args.input / "sft_sprint23.jsonl"
        if preferred.exists():
            files = [preferred]

    rows: list[dict] = []
    for f in files:
        rows.extend(_read_jsonl(f))

    blocked_ids, blocked_users = _held_out_blocklists(args.held_out)

    # Sprint 25 expansion held-outs (Tanglish / coding / tool honesty / mixed).
    sprint25_held_dir = _REPO / "training" / "data" / "held_out_eval"
    extra_held_files = [
        sprint25_held_dir / "eval_tanglish_sprint25.jsonl",
        sprint25_held_dir / "eval_coding_sprint25.jsonl",
        sprint25_held_dir / "eval_tanglish_coding_sprint25.jsonl",
        sprint25_held_dir / "eval_tool_honesty_sprint25.jsonl",
    ]
    if args.sprint25_balanced or args.sprint26_balanced:
        for extra in extra_held_files:
            if extra.exists():
                e_ids, e_users = _held_out_blocklists(extra)
                blocked_ids |= e_ids
                blocked_users |= e_users
        for ids_name in ("held_out_ids_sprint25.txt", "held_out_ids_sprint26.txt"):
            sprint_ids = sprint25_held_dir / ids_name
            if sprint_ids.exists():
                blocked_ids |= {
                    line.strip()
                    for line in sprint_ids.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.startswith("#")
                }
        if args.sprint26_balanced:
            s26_held = sprint25_held_dir / "eval_sprint26.jsonl"
            if s26_held.exists():
                e_ids, e_users = _held_out_blocklists(s26_held)
                blocked_ids |= e_ids
                blocked_users |= e_users

    if args.held_out_ids:
        args.held_out_ids.parent.mkdir(parents=True, exist_ok=True)
        # Preserve any pre-existing blocklist entries (do not clobber Sprint 25 ids).
        preexisting: set[str] = set()
        if args.held_out_ids.exists():
            preexisting = {
                line.strip()
                for line in args.held_out_ids.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            }
        blocked_ids |= preexisting
        args.held_out_ids.write_text(
            "\n".join(sorted(blocked_ids)) + ("\n" if blocked_ids else ""),
            encoding="utf-8",
        )
        extra = {
            line.strip()
            for line in args.held_out_ids.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        blocked_ids |= extra

    before = len(rows)
    filtered: list[dict] = []
    removed = 0
    for row in rows:
        eid = str(row.get("id", ""))
        users = user_contents(row)
        if eid in blocked_ids or any(u in blocked_users for u in users):
            removed += 1
            continue
        filtered.append(row)
    rows = filtered

    rng = random.Random(args.seed)
    rng.shuffle(rows)
    n_val = int(round(len(rows) * args.val_ratio)) if rows else 0
    val_rows = rows[:n_val]
    train_rows = rows[n_val:]

    _write_jsonl(args.train_out, train_rows)
    _write_jsonl(args.val_out, val_rows)

    overlap = assert_train_not_held_out(args.train_out, args.held_out, args.val_out)
    if overlap:
        print("ERROR: post-split leakage detected:")
        for err in overlap:
            print(f"  - {err}")
        return 1

    print(
        f"Input rows={before} kept={len(rows)} removed_held_out_overlap={removed} | "
        f"train={len(train_rows)} -> {args.train_out} | "
        f"val={len(val_rows)} -> {args.val_out} | "
        f"blocked_ids={len(blocked_ids)}"
    )
    print("held_out_eval remains separate and was not written into train/validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
