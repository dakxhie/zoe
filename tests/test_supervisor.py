"""Tests for supervisor agent routing and merging."""

from __future__ import annotations

from unittest.mock import patch

from agents.agent_result import AgentResult, Finding
from agents.state import Complexity, Intent, IntentType
from agents.supervisor import (
    merge_results,
    resolve_conflicts,
    select_specialists,
    should_use_supervisor,
)


def test_select_specialists_memory_query() -> None:
    intent = Intent(
        type=IntentType.MEMORY_RETRIEVAL,
        confidence=0.8,
        required_tools=("memory",),
        complexity=Complexity.LOW,
        primary_route="memory",
    )
    selected = select_specialists("What do you remember about me?", intent)
    assert "memory" in selected


def test_select_specialists_compare_frameworks() -> None:
    intent = Intent(
        type=IntentType.COMPARISON,
        confidence=0.7,
        required_tools=("web", "notes"),
        complexity=Complexity.MEDIUM,
        primary_route="web",
    )
    selected = select_specialists("Compare React and Vue", intent)
    assert "research" in selected
    assert "reasoning" in selected


def test_select_specialists_coding_adds_reasoning() -> None:
    selected = select_specialists("Fix this Python traceback in pipeline.py", None)
    assert "coding" in selected
    assert "reasoning" in selected


def test_select_specialists_creative_novel() -> None:
    selected = select_specialists("Write a fantasy novel about dragons", None)
    assert "creative" in selected
    assert "reasoning" in selected


def test_should_not_supervise_calculator() -> None:
    intent = Intent(
        type=IntentType.CALCULATOR,
        confidence=0.9,
        required_tools=(),
        complexity=Complexity.LOW,
        primary_route="chat",
    )
    assert should_use_supervisor(intent, "2+2") is False


def test_should_not_supervise_simple_chat() -> None:
    intent = Intent(
        type=IntentType.CONVERSATION,
        confidence=0.5,
        required_tools=("chat",),
        complexity=Complexity.LOW,
        primary_route="chat",
    )
    assert should_use_supervisor(intent, "Hello") is False


def test_resolve_conflicts_prefers_higher_confidence() -> None:
    low = AgentResult(
        agent="research",
        confidence=0.6,
        findings=[Finding(summary="Vue is simpler", topic="framework")],
    )
    high = AgentResult(
        agent="memory",
        confidence=0.92,
        findings=[Finding(summary="User prefers React", topic="framework")],
    )
    merged = resolve_conflicts([low, high])
    summaries = [f.summary for r in merged for f in r.findings]
    assert "User prefers React" in summaries
    assert "Vue is simpler" not in summaries


def test_merge_results_includes_header() -> None:
    results = [
        AgentResult(
            agent="memory",
            confidence=0.9,
            findings=[Finding(summary="Favorite color is blue", topic="profile")],
        )
    ]
    text = merge_results(results)
    assert "Internal Specialist Brief" in text
    assert "Favorite color is blue" in text


@patch("agents.supervisor.run_specialists_parallel")
def test_run_supervisor_cycle_attaches_metadata(mock_parallel) -> None:
    from agents.state import AgentState
    from agents.supervisor import run_supervisor_cycle

    mock_parallel.return_value = [
        AgentResult(agent="memory", confidence=0.9, findings=[Finding(summary="Alice")])
    ]
    intent = Intent(
        type=IntentType.MEMORY_RETRIEVAL,
        confidence=0.8,
        required_tools=("memory",),
        complexity=Complexity.LOW,
        primary_route="memory",
    )
    state = AgentState(conversation_id="test", goal="What do you know about me?")
    brief = run_supervisor_cycle("What do you know about me?", intent, state)

    assert brief.context
    assert state.metadata.get("supervisor", {}).get("agents")
