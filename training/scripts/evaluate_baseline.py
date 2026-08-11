"""Baseline vs adapter evaluation entrypoint.

Does not run model inference unless explicitly invoked with --execute
AND --i-understand-this-loads-models.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from training.evaluation.runner import (  # noqa: E402
    EvaluationPlan,
    describe_plan,
    run_evaluation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate base vs fine-tuned Zoe (opt-in execute)."
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
        "--output",
        type=Path,
        default=None,
        help="Where to write generations JSON (default under training/adapters/)",
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
    default_out = (
        _REPO / "training" / "adapters" / "runs" / "sprint24_pilot" / "eval_baseline.json"
    )
    if "adapter" in modes and "base" in modes:
        default_out = (
            _REPO
            / "training"
            / "adapters"
            / "runs"
            / "sprint24_pilot"
            / "eval_base_vs_adapter.json"
        )
    elif modes == ["adapter"]:
        default_out = (
            _REPO / "training" / "adapters" / "runs" / "sprint24_pilot" / "eval_adapter.json"
        )

    plan = EvaluationPlan(
        config_path=args.config,
        split=args.split,
        modes=modes,
        adapter_path=args.adapter_path,
        output_path=args.output or default_out,
    )
    print(describe_plan(plan))
    print(f"  output: {plan.output_path}")

    if not args.execute:
        print("Dry plan only. Pass --execute --i-understand-this-loads-models to run.")
        return 0
    if not args.ack_load:
        print("Refusing: --execute requires --i-understand-this-loads-models")
        return 2

    return run_evaluation(plan)


if __name__ == "__main__":
    raise SystemExit(main())
