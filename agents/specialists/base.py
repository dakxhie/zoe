"""Base types for internal specialist agents."""

from __future__ import annotations

from typing import Protocol

from agents.agent_result import AgentResult
from agents.state import Intent


class SpecialistAgent(Protocol):
    """Protocol for specialist agents."""

    name: str

    def run(self, query: str, intent: Intent | None) -> AgentResult:
        """Gather structured findings for the supervisor."""


def clamp_confidence(value: float) -> float:
    """Clamp confidence to 0.0–1.0."""
    return max(0.0, min(1.0, value))
