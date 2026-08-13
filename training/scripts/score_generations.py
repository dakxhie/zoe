"""Score held-out generations with heuristics (no model loading).

Can rebuild baseline_scores.json / baseline_report.md from a generations JSONL
or a legacy combined eval JSON. Human rubric scoring remains authoritative.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from training.evaluation.artifacts import (  # noqa: E402
    build_report_markdown,
    build_scores_payload,
    heuristic_flags,
    verify_mode_artifacts,
)


def _load_generations(path: Path) -> tuple[dict, list[dict]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}, []
    if path.suffix == ".jsonl" or text.startswith("{"):
        # JSONL if multiple lines starting with {, else maybe single JSON object.
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if path.suffix == ".jsonl" or (
            len(lines) > 1 and all(ln.lstrip().startswith("{") for ln in lines)
        ):
            rows = [json.loads(ln) for ln in lines]
            meta = {}
            if rows and isinstance(rows[0].get("run_meta"), dict):
                meta = rows[0]["run_meta"]
            return meta, rows
    data = json.loads(text)
    if isinstance(data, list):
        return {}, data
    return data.get("run_meta") or {}, data.get("results") or []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Heuristic score for Zoe eval generations (no model load)."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="baseline_generations.jsonl or legacy eval JSON",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help="Where to write *_scores.json and *_report.md (default: input parent)",
    )
    parser.add_argument(
        "--mode",
        default=None,
        help="base|adapter (default: infer from rows or 'base')",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional extra dump of scored rows (legacy)",
    )
    args = parser.parse_args(argv)

    run_meta, results = _load_generations(args.input)
    if not results:
        print(f"No generations found in {args.input}")
        return 1

    modes = sorted({str(r.get("mode") or "base") for r in results})
    if args.mode:
        modes = [args.mode]

    artifact_dir = args.artifact_dir or args.input.parent
    artifact_dir.mkdir(parents=True, exist_ok=True)

    for mode in modes:
        # Ensure flags exist for any legacy rows.
        for row in results:
            if row.get("mode") == mode and "flags" not in row:
                row.setdefault("auto_metrics", {})
        scores = build_scores_payload(
            mode=mode,
            generations=results,
            run_meta=run_meta
            or {
                "split_path": "unknown",
                "model_name": "unknown",
                "n_examples": len([r for r in results if r.get("mode") == mode]),
            },
            artifact_dir=artifact_dir,
        )
        # Attach per-example heuristic flags into scores (already done in builder).
        prefix = "baseline" if mode == "base" else "adapter"
        scores_path = artifact_dir / f"{prefix}_scores.json"
        report_path = artifact_dir / f"{prefix}_report.md"
        gen_path = artifact_dir / f"{prefix}_generations.jsonl"
        if not gen_path.exists() and args.input.name.endswith(".jsonl"):
            gen_path = args.input
        scores_path.write_text(
            json.dumps(scores, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        report_path.write_text(
            build_report_markdown(scores, generations_path=gen_path),
            encoding="utf-8",
        )
        ok, errors = verify_mode_artifacts(artifact_dir, mode=mode)
        print(f"Wrote {scores_path}")
        print(f"Wrote {report_path}")
        if not ok:
            print("VERIFY FAIL after rescore:")
            for err in errors:
                print(f"  - {err}")
            return 1
        print(
            json.dumps(
                {
                    "mode": mode,
                    "counts": scores.get("counts"),
                    "heuristic_flag_rates": scores.get("heuristic_flag_rates"),
                    "verified": True,
                },
                indent=2,
            )
        )

    if args.output is not None:
        scored = []
        for r in results:
            if args.mode and r.get("mode") != args.mode:
                continue
            scored.append(
                {
                    "id": r.get("id"),
                    "mode": r.get("mode"),
                    "flags": heuristic_flags(r),
                    "response_chars": len(r.get("response") or ""),
                }
            )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {
                    "source": str(args.input),
                    "run_meta": run_meta,
                    "note": "Heuristic only — human rubric required for ship decisions.",
                    "scored": scored,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Wrote legacy scored dump {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
