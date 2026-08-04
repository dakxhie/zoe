"""Tests for specialist conflict resolution."""

from __future__ import annotations

from agents.agent_result import AgentResult, Finding
from agents.supervisor import merge_results, resolve_conflicts


def test_conflict_resolution_keeps_stronger_evidence() -> None:
    a = AgentResult(
        agent="research",
        confidence=0.55,
        findings=[Finding(summary="Answer A", topic="t1")],
    )
    b = AgentResult(
        agent="memory",
        confidence=0.95,
        findings=[Finding(summary="Answer B", topic="t1")],
    )
    resolved = resolve_conflicts([a, b])
    texts = [f.summary for r in resolved for f in r.findings]
    assert texts == ["Answer B"]


def test_merge_preserves_multiple_agents() -> None:
    results = [
        AgentResult(agent="memory", confidence=0.9, findings=[Finding(summary="M1", topic="a")]),
        AgentResult(agent="research", confidence=0.85, findings=[Finding(summary="R1", topic="b")]),
    ]
    merged = merge_results(results)
    assert "Memory Specialist" in merged
    assert "Research Specialist" in merged
