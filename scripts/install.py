#!/usr/bin/env python3
"""Zoe installation helper — verify folders and optional dependencies."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from deployment.config import load_config
    from deployment.startup import run_startup_sequence

    load_config()
    report = run_startup_sequence()
    print("Zoe install verification")
    for name, seconds in report.steps:
        print(f"  OK {name} ({seconds:.2f}s)")
    if report.messages:
        for msg in report.messages:
            print(f"  WARN {msg}")
    print("Optional: pip install -r requirements-voice.txt for voice")
    return 0 if report.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
