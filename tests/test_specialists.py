"""Tests for specialist agents."""

from __future__ import annotations

from unittest.mock import patch

from agents.specialists.coding_agent import CodingSpecialist, coding_specialist_relevant
from agents.specialists.creative_agent import CreativeSpecialist
from agents.specialists.memory_agent import MemorySpecialist
from agents.specialists.reasoning_agent import ReasoningSpecialist
from agents.specialists.research_agent import ResearchSpecialist
from agents.state import Complexity, Intent, IntentType


def test_memory_specialist_returns_structured_result() -> None:
    specialist = MemorySpecialist()
    with patch("memory.retriever.search_memories", return_value=[{"content": "My name is Alice", "id": "1", "created_at": ""}]):
        result = specialist.run("What is my name?", None)
    assert result.agent == "memory"
    assert 0.0 <= result.confidence <= 1.0
    assert result.findings


def test_research_specialist_handles_empty_indexes() -> None:
    specialist = ResearchSpecialist()
    with patch("pdf.retriever.search_documents", return_value=[]), patch(
        "codebase.retriever.search_code",
        return_value=[],
    ), patch("web.retriever.retrieve_web_context_with_stats", return_value=("", {"pages_retrieved": 0})):
        result = specialist.run("Compare React and Vue", None)
    assert result.agent == "research"
    assert result.warnings


def test_coding_specialist_project_analysis() -> None:
    assert coding_specialist_relevant("Analyze this Python project", None) is True
    specialist = CodingSpecialist()
    with patch("codebase.retriever.search_code", return_value=[]):
        result = specialist.run("Fix this Python bug in pipeline", None)
    assert result.agent == "coding"


def test_reasoning_specialist_comparison_frame() -> None:
    intent = Intent(
        type=IntentType.COMPARISON,
        confidence=0.7,
        required_tools=("web",),
        complexity=Complexity.MEDIUM,
        primary_route="web",
    )
    result = ReasoningSpecialist().run("Compare SQL and NoSQL", intent)
    assert any("comparison" in (f.topic or "") or "comparison" in f.summary.lower() for f in result.findings)


def test_creative_specialist_brainstorm() -> None:
    result = CreativeSpecialist().run("Brainstorm names for my startup", None)
    assert result.confidence >= 0.7
    assert result.findings
