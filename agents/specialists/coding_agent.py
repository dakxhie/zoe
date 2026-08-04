"""Coding specialist: code search, architecture, debugging context."""

from __future__ import annotations

import logging

from agents.agent_result import AgentResult, Citation, Finding
from agents.specialists.base import clamp_confidence
from agents.state import Intent
from agents.planner import is_project_analysis_query
from core.text_utils import matches_any, normalize_text

logger = logging.getLogger(__name__)

CODING_PHRASES: tuple[str, ...] = (
    "code",
    "python",
    "debug",
    "refactor",
    "function",
    "class ",
    "architecture",
    "stack trace",
    "error",
    "bug",
    "test",
    "optimize",
    "implement",
)


class CodingSpecialist:
    name = "coding"

    def run(self, query: str, intent: Intent | None) -> AgentResult:
        findings: list[Finding] = []
        citations: list[Citation] = []
        warnings: list[str] = []
        confidence = 0.45

        if intent and intent.primary_route == "code":
            confidence = 0.75
        if is_project_analysis_query(query):
            confidence = 0.85

        try:
            from codebase.retriever import search_code

            terms = [query, "generate_response", "execute_tool", "orchestrate"]
            seen: set[str] = set()
            for term in terms:
                for hit in search_code(term, top_k=3):
                    key = hit.get("path", "") + hit.get("content", "")[:40]
                    if key in seen:
                        continue
                    seen.add(key)
                    findings.append(
                        Finding(
                            summary=f"[{hit.get('path')}] {hit.get('content', '')[:320]}",
                            source="code",
                            topic="implementation",
                        )
                    )
            if findings:
                confidence = max(confidence, 0.78)
                citations.append(Citation(source="code", label="Repository code index"))
        except Exception as exc:
            logger.debug("Coding specialist search failed: %s", exc)
            warnings.append(str(exc))

        if is_project_analysis_query(query):
            try:
                from agents.project_report import build_project_report, format_project_report

                report = format_project_report(build_project_report())
                findings.append(
                    Finding(
                        summary="Structured project report available.",
                        detail=report[:1200],
                        source="project_report",
                        topic="architecture",
                    )
                )
                confidence = max(confidence, 0.88)
            except Exception as exc:
                logger.debug("Coding specialist project report failed: %s", exc)

        if not findings:
            warnings.append("No indexed code matches; run code indexing if needed.")

        return AgentResult(
            agent=self.name,
            confidence=clamp_confidence(confidence),
            findings=findings,
            citations=citations,
            warnings=warnings,
        )


def coding_specialist_relevant(query: str, intent: Intent | None) -> bool:
    normalized = normalize_text(query)
    if is_project_analysis_query(query):
        return True
    if intent and intent.primary_route == "code":
        return True
    if intent and intent.type.value == "project_analysis":
        return True
    return matches_any(normalized, CODING_PHRASES)
