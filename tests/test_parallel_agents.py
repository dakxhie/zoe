"""Tests for parallel specialist execution."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agents.agent_result import AgentResult
from agents.coordinator import run_specialists_parallel
from agents.state import Complexity, Intent, IntentType


def test_parallel_runs_all_selected_agents() -> None:
    intent = Intent(
        type=IntentType.MULTI_TOOL,
        confidence=0.7,
        required_tools=("memory", "web"),
        complexity=Complexity.HIGH,
        primary_route="web",
    )

    memory = MagicMock()
    memory.run.return_value = AgentResult(agent="memory", confidence=0.9)
    research = MagicMock()
    research.run.return_value = AgentResult(agent="research", confidence=0.8)

    registry = {"memory": memory, "research": research}
    with patch.dict("agents.coordinator.SPECIALIST_REGISTRY", registry, clear=True):
        results = run_specialists_parallel("Compare notes and web facts", intent, ("memory", "research"))

    assert len(results) == 2
    memory.run.assert_called_once()
    research.run.assert_called_once()


def test_parallel_single_agent_no_thread_pool() -> None:
    memory = MagicMock()
    memory.run.return_value = AgentResult(agent="memory", confidence=0.5)
    with patch.dict("agents.coordinator.SPECIALIST_REGISTRY", {"memory": memory}, clear=True):
        results = run_specialists_parallel("About me", None, ("memory",))
    assert len(results) == 1
