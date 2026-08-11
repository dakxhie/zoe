"""Validate SFT or correction JSONL datasets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from training.schema import PERSONALITY_BALANCE_TARGETS  # noqa: E402
from training.schema.validate import validate_paths  # noqa: E402


def _personality_counts(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    files = [path] if path.is_file() else sorted(path.glob("*.jsonl"))
    for f in files:
        for raw in f.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            obj = json.loads(line)
            mode = (obj.get("metadata") or {}).get("personality_mode", "unknown")
            counts[mode] = counts.get(mode, 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Zoe fine-tuning JSONL.")
    parser.add_argument(
        "--path",
        type=Path,
        required=True,
        help="JSONL file or directory",
    )
    parser.add_argument(
        "--kind",
        choices=("sft", "correction"),
        default="sft",
    )
    parser.add_argument(
        "--show-personality-balance",
        action="store_true",
        help="Print personality_mode distribution vs targets",
    )
    args = parser.parse_args(argv)

    report = validate_paths([args.path], kind=args.kind)
    print(report.summary())
    for err in report.errors:
        print(f"ERROR {err.path}:{err.line} [{err.code}] {err.message}")
    for warn in report.warnings:
        print(f"WARN  {warn.path}:{warn.line} [{warn.code}] {warn.message}")

    if args.show_personality_balance and args.kind == "sft":
        counts = _personality_counts(args.path)
        total = sum(counts.values()) or 1
        print("Personality balance:")
        for mode, (lo, hi) in PERSONALITY_BALANCE_TARGETS.items():
            n = counts.get(mode, 0)
            pct = n / total
            flag = "n<20" if total < 20 else ("OK" if lo <= pct <= hi else "CHECK")
            print(f"  {mode}: {n} ({pct:.1%}) target {lo:.0%}-{hi:.0%} [{flag}]")
        extra = set(counts) - set(PERSONALITY_BALANCE_TARGETS)
        for mode in sorted(extra):
            print(f"  {mode}: {counts[mode]} (unexpected)")

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
