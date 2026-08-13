"""Baseline vs adapter evaluation entrypoint.

Does not run model inference unless explicitly invoked with --execute
AND --i-understand-this-loads-models.

Without those flags this script ONLY prints a plan and writes nothing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from training.evaluation.artifacts import default_sprint26_artifact_dir  # noqa: E402
from training.evaluation.runner import (  # noqa: E402
    EvaluationPlan,
    describe_plan,
    run_evaluation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate base vs fine-tuned Zoe (opt-in execute). "
            "Dry run writes no artifacts."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=_REPO / "training" / "config" / "colab_qlora.yaml",
    )
    parser.add_argument(
        "--split",
        default="held_out_eval",
        choices=("held_out_eval", "validation"),
    )
    parser.add_argument(
        "--compare",
        default="base",
        help="Comma list: base and/or adapter. Default base-only for baseline.",
    )
    parser.add_argument(
        "--adapter-path",
        type=Path,
        default=None,
        help="Path to PEFT adapter (required if compare includes adapter and --execute)",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help=(
            "Directory for baseline_/adapter_ generations, scores, and report "
            f"(default: {default_sprint26_artifact_dir(_REPO)})"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Optional legacy combined JSON dump. Primary artifacts always go to "
            "--artifact-dir (Sprint 26 layout)."
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually run generation. Without this flag, only prints the plan.",
    )
    parser.add_argument(
        "--i-understand-this-loads-models",
        action="store_true",
        dest="ack_load",
        help="Required together with --execute to load weights.",
    )
    args = parser.parse_args(argv)

    modes = [m.strip() for m in args.compare.split(",") if m.strip()]
    artifact_dir = args.artifact_dir or default_sprint26_artifact_dir(_REPO)

    plan = EvaluationPlan(
        config_path=args.config,
        split=args.split,
        modes=modes,
        adapter_path=args.adapter_path,
        output_path=args.output,
        artifact_dir=artifact_dir,
    )
    print(describe_plan(plan))
    print(f"  expected_artifacts_under: {artifact_dir}")
    if modes == ["base"]:
        print("  expected_files:")
        print(f"    - {artifact_dir / 'baseline_generations.jsonl'}")
        print(f"    - {artifact_dir / 'baseline_scores.json'}")
        print(f"    - {artifact_dir / 'baseline_report.md'}")

    if not args.execute:
        print()
        print("DRY PLAN ONLY — NO BASELINE ARTIFACTS WERE WRITTEN.")
        print(
            "To measure the unmodified base model on Sprint 26 held-out, run:"
        )
        print(
            "  python -m training.scripts.evaluate_baseline "
            "--config training/config/colab_qlora.yaml "
            "--split held_out_eval --compare base "
            "--execute --i-understand-this-loads-models"
        )
        return 0
    if not args.ack_load:
        print("Refusing: --execute requires --i-understand-this-loads-models")
        return 2

    if "adapter" in modes and args.adapter_path is None:
        print("Refusing: adapter compare requires --adapter-path")
        return 2

    return run_evaluation(plan)


if __name__ == "__main__":
    raise SystemExit(main())
