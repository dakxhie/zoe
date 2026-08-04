#!/usr/bin/env python3
"""Run Zoe benchmark suite and print JSON report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Zoe benchmark suite")
    parser.add_argument("--model", action="store_true", help="Include model latency benchmarks")
    args = parser.parse_args()

    from deployment.benchmark import run_benchmark_suite
    from deployment.config import load_config

    load_config()
    report = run_benchmark_suite(include_model=args.model)
    print(json.dumps(report.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
