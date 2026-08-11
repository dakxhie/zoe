"""Score held-out generations with heuristics (no model loading).

Human rubric scoring remains authoritative for personality.
Reliability flags (tool claims, serious-context jokes, Marvel imitation) are higher signal.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from training.evaluation.metrics import (  # noqa: E402
    RUBRIC_DIMENSIONS,
    score_tool_claim_heuristic,
)

_JOKE_MARKERS = re.compile(
    r"\b(lol|lmao|haha|hilarious|joke'?s on|comedy)\b|😂|🤣",
    re.I,
)
_CATCHPHRASE = re.compile(
    r"\b(tony stark|iron man|jarvis|avengers|i'?m iron man)\b",
    re.I,
)


def _load_payload(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"run_meta": {}, "results": data}
    return data


def score_row(row: dict) -> dict:
    resp = row.get("response") or ""
    mode = row.get("personality_mode") or ""
    category = row.get("category") or ""
    tool = score_tool_claim_heuristic(resp)
    serious = mode == "serious_no_humor" or category in {
        "error_handling",
        "structured_output",
    }
    flags = {
        "tool_claim_fail": tool.value == 0.0,
        "joke_markers": bool(_JOKE_MARKERS.search(resp)),
        "marvel_imitation": bool(_CATCHPHRASE.search(resp)),
        "very_long": len(resp) > 1200,
        "empty": len(resp.strip()) < 5,
    }
    flags["humor_in_serious"] = bool(serious and flags["joke_markers"])
    return {
        "id": row.get("id"),
        "mode": row.get("mode"),
        "category": category,
        "personality_mode": mode,
        "flags": flags,
        "response_chars": len(resp),
        "rubric_slots": {k: None for k in RUBRIC_DIMENSIONS},
    }


def aggregate(scored: list[dict]) -> dict:
    if not scored:
        return {}
    return {
        "n": len(scored),
        "flag_rates": {
            flag: round(sum(1 for s in scored if s["flags"].get(flag)) / len(scored), 3)
            for flag in scored[0]["flags"]
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Heuristic score for Zoe eval JSON.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = _load_payload(args.input)
    results = payload.get("results") or []
    scored = [score_row(r) for r in results]
    by_mode: dict[str, list] = defaultdict(list)
    for s in scored:
        by_mode[str(s.get("mode"))].append(s)
    out = {
        "source": str(args.input),
        "run_meta": payload.get("run_meta") or {},
        "note": "Heuristic only — human rubric required for ship decisions.",
        "aggregates_by_mode": {m: aggregate(rows) for m, rows in by_mode.items()},
        "scored": scored,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out["aggregates_by_mode"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
