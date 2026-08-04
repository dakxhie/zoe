"""Specialist agents for Zoe AI multi-agent reasoning."""

from agents.specialists.coding_agent import CodingSpecialist
from agents.specialists.creative_agent import CreativeSpecialist
from agents.specialists.memory_agent import MemorySpecialist
from agents.specialists.reasoning_agent import ReasoningSpecialist
from agents.specialists.research_agent import ResearchSpecialist

SPECIALIST_REGISTRY: dict[str, object] = {
    "memory": MemorySpecialist(),
    "research": ResearchSpecialist(),
    "coding": CodingSpecialist(),
    "reasoning": ReasoningSpecialist(),
    "creative": CreativeSpecialist(),
}

__all__ = [
    "SPECIALIST_REGISTRY",
    "CodingSpecialist",
    "CreativeSpecialist",
    "MemorySpecialist",
    "ReasoningSpecialist",
    "ResearchSpecialist",
]
