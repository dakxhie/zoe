"""Creative specialist: writing, brainstorming, ideation frames."""

from __future__ import annotations

from agents.agent_result import AgentResult, Finding
from agents.specialists.base import clamp_confidence
from agents.state import Intent
from core.text_utils import matches_any, normalize_text

CREATIVE_PHRASES: tuple[str, ...] = (
    "story",
    "novel",
    "poem",
    "brainstorm",
    "idea",
    "name for",
    "marketing",
    "slogan",
    "design",
    "creative",
    "fantasy",
    "character",
    "plot",
)


class CreativeSpecialist:
    name = "creative"

    def run(self, query: str, intent: Intent | None) -> AgentResult:
        normalized = normalize_text(query)
        findings: list[Finding] = []
        confidence = 0.45

        if matches_any(normalized, CREATIVE_PHRASES):
            confidence = 0.72
            if matches_any(normalized, ("novel", "story", "fantasy", "chapter")):
                findings.append(
                    Finding(
                        summary="Long-form creative request: outline setting, characters, tone, and plot beats.",
                        topic="narrative",
                    )
                )
            elif matches_any(normalized, ("brainstorm", "idea", "name for")):
                findings.append(
                    Finding(
                        summary="Ideation request: produce diverse options with brief rationale.",
                        topic="brainstorm",
                    )
                )
            else:
                findings.append(
                    Finding(
                        summary="Creative writing request: match tone, audience, and format.",
                        topic="writing",
                    )
                )

        return AgentResult(
            agent=self.name,
            confidence=clamp_confidence(confidence),
            findings=findings,
        )


def creative_specialist_relevant(query: str, intent: Intent | None) -> bool:
    return matches_any(normalize_text(query), CREATIVE_PHRASES)
