#!/usr/bin/env python3
"""Extended doctor: core checks + deployment health."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from deployment.config import load_config
    from deployment.diagnostics import run_deployment_diagnostics
    from deployment.health import overall_health, run_health_checks

    load_config()

    from core.doctor import print_doctor_report, run_doctor

    print_doctor_report(run_doctor())
    print()
    print("=== Deployment health ===")
    checks = run_health_checks()
    print(f"Overall: {overall_health(checks).value}")
    for check in checks:
        detail = "; ".join(check.details[:2])
        print(f"  [{check.status.value}] {check.name}: {detail}")

    diag = run_deployment_diagnostics()
    if diag.lines:
        print()
        print("=== Deployment diagnostics ===")
        for line in diag.lines:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
