"""Dataset schema types and constants for Zoe SFT data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant"]

CATEGORIES: tuple[str, ...] = (
    "general_conversation",
    "personality",
    "tool_routing",
    "agent_planning",
    "memory",
    "retrieval_rag",
    "coding",
    "project_analysis",
    "structured_output",
    "error_handling",
)

PERSONALITY_MODES: tuple[str, ...] = (
    "professional_neutral",
    "lightly_witty",
    "playful_sarcastic",
    "serious_no_humor",
)

# Target distribution for initial curated sets (guidance, not hard-enforced).
PERSONALITY_BALANCE_TARGETS: dict[str, tuple[float, float]] = {
    "professional_neutral": (0.55, 0.65),
    "lightly_witty": (0.15, 0.20),
    "playful_sarcastic": (0.05, 0.10),
    "serious_no_humor": (0.10, 0.20),
}

DIFFICULTIES: tuple[str, ...] = ("easy", "medium", "hard")

ALLOWED_ROLES: frozenset[str] = frozenset({"system", "user", "assistant"})


@dataclass
class ChatMessage:
    role: Role
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class ExampleMetadata:
    category: str
    difficulty: str = "medium"
    source: str = "seed"
    quality: float = 1.0
    personality_mode: str = "professional_neutral"
    personality_required: bool = False
    tool_required: bool = False
    expected_behavior: str = ""
    safety_sensitive: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "category": self.category,
            "difficulty": self.difficulty,
            "source": self.source,
            "quality": self.quality,
            "personality_mode": self.personality_mode,
            "personality_required": self.personality_required,
            "tool_required": self.tool_required,
            "expected_behavior": self.expected_behavior,
            "safety_sensitive": self.safety_sensitive,
        }
        if self.extra:
            payload["extra"] = self.extra
        return payload


@dataclass
class SFTExample:
    """One supervised fine-tuning conversation.

    Only ``messages`` are ever fed to the model. ``metadata`` is bookkeeping.
    """

    id: str
    messages: list[ChatMessage]
    metadata: ExampleMetadata

    def to_training_messages(self) -> list[dict[str, str]]:
        """Return chat messages only (no metadata)."""
        return [m.to_dict() for m in self.messages]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata.to_dict(),
        }


@dataclass
class CorrectionExample:
    """Failure → correction record for later preference / corrective SFT."""

    id: str
    user_request: str
    bad_response: str
    why_bad: str
    ideal_response: str
    lesson: str
    category: str = "error_handling"
    source: str = "regression_inspired"
    safety_sensitive: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_request": self.user_request,
            "bad_response": self.bad_response,
            "why_bad": self.why_bad,
            "ideal_response": self.ideal_response,
            "lesson": self.lesson,
            "category": self.category,
            "source": self.source,
            "safety_sensitive": self.safety_sensitive,
        }

    def to_sft_example(self, system_prompt: str) -> SFTExample:
        """Convert to SFT using the ideal response only (bad response stays in metadata)."""
        return SFTExample(
            id=self.id,
            messages=[
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=self.user_request),
                ChatMessage(role="assistant", content=self.ideal_response),
            ],
            metadata=ExampleMetadata(
                category=self.category,
                source=self.source,
                personality_mode="serious_no_humor"
                if self.safety_sensitive
                else "professional_neutral",
                expected_behavior=self.lesson,
                safety_sensitive=self.safety_sensitive,
                extra={
                    "correction": True,
                    "why_bad": self.why_bad,
                    "bad_response_hash_hint": "stored_separately_not_for_model_input",
                },
            ),
        )


DEFAULT_SYSTEM_PROMPT = (
    "You are Zoe, a local personal AI assistant. Be professional, intelligent, "
    "clear, and useful. When the context allows, you may be lightly witty or "
    "playfully sarcastic—never insulting, never at the expense of accuracy or "
    "safety. Humor is optional seasoning; in serious or high-stakes situations, "
    "stay direct and calm. Do not invent tool results, file contents, or facts "
    "that were not provided. Admit uncertainty."
)
