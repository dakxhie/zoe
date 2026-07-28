"""Smoke test for project analysis planning and execution."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.analyzer import run_project_analysis
from agents.planner import build_plan, is_project_analysis_query


def main() -> None:
    """Verify project analysis detection, planning, and context gathering."""
    query = "Analyze this Python project and tell me how to improve it."

    if not is_project_analysis_query(query):
        raise SystemExit("Project analysis query was not detected")

    plan = build_plan()
    expected_steps = [
        "Search code",
        "Read important files",
        "Gather context",
        "Summarize",
        "Recommend improvements",
    ]

    if plan != expected_steps:
        raise SystemExit("Project analysis plan is incorrect")

    is_analysis, context = run_project_analysis(query)

    if not is_analysis:
        raise SystemExit("Project analysis was not triggered")

    for step in expected_steps:
        if step not in context:
            raise SystemExit(f'Missing plan step in context: "{step}"')

    if "Project Analysis" not in context:
        raise SystemExit("Gathered project analysis context is missing")

    if "README.md" not in context:
        raise SystemExit("Important project files were not read")

    print("Plan:")
    for index, step in enumerate(plan, start=1):
        print(f"{index}. {step}")

    print("\nGathered context preview:")
    print(context[:500])
    print("\nProject analysis tests passed.")


if __name__ == "__main__":
    main()
