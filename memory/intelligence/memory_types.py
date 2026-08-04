"""Memory type taxonomy and scored memory records."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MemoryType(str, Enum):
    """Categories of long-term memory Zoe maintains."""

    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PREFERENCE = "preference"
    IDENTITY = "identity"
    PROJECT = "project"
    EPISODE = "episode"
    TEMPORARY = "temporary"


@dataclass
class ScoredMemory:
    """A memory candidate with intelligence metadata."""

    text: str
    memory_type: MemoryType
    category: str
    importance: float
    confidence: float
    frequency: int = 1
    last_used: str = ""
    created: str = ""
    expires_at: str = ""
    explicit: bool = False
    source: str = "conversation"
    metadata: dict[str, str] = field(default_factory=dict)

    def clamp_scores(self) -> None:
        self.importance = max(0.0, min(1.0, self.importance))
        self.confidence = max(0.0, min(1.0, self.confidence))
        self.frequency = max(1, self.frequency)
