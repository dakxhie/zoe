"""Zoe AI end-to-end regression test entrypoint.

Usage:
    python tests/regression.py
    python tests/regression.py --full
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Zoe AI regression tests")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run the complete regression suite (indexes, web, vision, imports, performance)",
    )
    args = parser.parse_args()

    from tests.regression.runner import run_regression

    return run_regression(full=args.full)


if __name__ == "__main__":
    raise SystemExit(main())
