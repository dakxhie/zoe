"""Inspect dataset composition without training."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Zoe SFT JSONL composition.")
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=3, help="Print N example ids")
    args = parser.parse_args(argv)

    files = [args.path] if args.path.is_file() else sorted(args.path.glob("*.jsonl"))
    categories: Counter[str] = Counter()
    modes: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    difficulties: Counter[str] = Counter()
    tool_req = 0
    safety = 0
    total = 0
    ids: list[str] = []

    for f in files:
        for raw in f.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            obj = json.loads(line)
            total += 1
            ids.append(str(obj.get("id", "")))
            meta = obj.get("metadata") or {}
            categories[str(meta.get("category", "?"))] += 1
            modes[str(meta.get("personality_mode", "?"))] += 1
            sources[str(meta.get("source", "?"))] += 1
            difficulties[str(meta.get("difficulty", "?"))] += 1
            if meta.get("tool_required"):
                tool_req += 1
            if meta.get("safety_sensitive"):
                safety += 1

    print(f"files={len(files)} examples={total}")
    print("categories:", dict(categories))
    print("personality_modes:", dict(modes))
    print("sources:", dict(sources))
    print("difficulties:", dict(difficulties))
    print(f"tool_required={tool_req} safety_sensitive={safety}")
    print("sample ids:", ids[: args.samples])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
