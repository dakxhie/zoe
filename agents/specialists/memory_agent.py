"""Memory specialist: semantic memory, history, notes, user profile."""

from __future__ import annotations

import logging

from agents.agent_result import AgentResult, Citation, Finding
from agents.specialists.base import clamp_confidence
from agents.state import Intent
from core.text_utils import matches_any, normalize_text

logger = logging.getLogger(__name__)

MEMORY_PHRASES: tuple[str, ...] = (
    "remember",
    "about me",
    "my name",
    "my favorite",
    "what do you know",
    "what do you recall",
    "user profile",
    "long-term",
)


class MemorySpecialist:
    name = "memory"

    def run(self, query: str, intent: Intent | None) -> AgentResult:
        findings: list[Finding] = []
        citations: list[Citation] = []
        warnings: list[str] = []
        confidence = 0.35

        try:
            from memory.retriever import search_memories

            memory_hits = search_memories(query, top_k=5)
            if memory_hits:
                confidence = clamp_confidence(0.5 + 0.08 * len(memory_hits))
                for hit in memory_hits[:5]:
                    findings.append(
                        Finding(
                            summary=hit["content"][:300],
                            source="zoe_memory",
                            topic="memory",
                        )
                    )
                citations.append(Citation(source="memory", label="Learned memories"))
        except Exception as exc:
            logger.debug("Memory specialist search_memories failed: %s", exc)
            warnings.append(str(exc))

        try:
            from conversation.retriever import search_history

            history_hits = search_history(query, top_k=3)
            for hit in history_hits:
                role = hit.get("role", "user")
                content = hit.get("content", "")
                if content.strip():
                    findings.append(
                        Finding(
                            summary=f"{role}: {content[:200]}",
                            source="conversation_history",
                            topic="episodic",
                        )
                    )
            if history_hits:
                confidence = max(confidence, clamp_confidence(0.55 + 0.05 * len(history_hits)))
                citations.append(Citation(source="history", label="Conversation history"))
        except Exception as exc:
            logger.debug("Memory specialist history search failed: %s", exc)

        try:
            from rag.retriever import search

            note_hits = search(query, top_k=3)
            for hit in note_hits:
                text = hit.get("content") or hit.get("document") or str(hit)
                if str(text).strip():
                    findings.append(
                        Finding(
                            summary=str(text)[:250],
                            source="notes",
                            topic="notes",
                        )
                    )
            if note_hits:
                confidence = max(confidence, 0.6)
                citations.append(Citation(source="notes", label="Personal notes"))
        except Exception as exc:
            logger.debug("Memory specialist notes search failed: %s", exc)

        if not findings:
            warnings.append("No memory, history, or note matches found.")
            confidence = 0.2

        return AgentResult(
            agent=self.name,
            confidence=clamp_confidence(confidence),
            findings=findings,
            citations=citations,
            warnings=warnings,
        )


def memory_specialist_relevant(query: str, intent: Intent | None) -> bool:
    normalized = normalize_text(query)
    if intent and intent.primary_route == "memory":
        return True
    if intent and intent.type.value == "memory_retrieval":
        return True
    return matches_any(normalized, MEMORY_PHRASES)
