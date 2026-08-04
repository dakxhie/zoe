"""Research specialist: web, PDFs, documentation, indexed code."""

from __future__ import annotations

import logging

from agents.agent_result import AgentResult, Citation, Finding
from agents.specialists.base import clamp_confidence
from agents.state import Intent
from core.text_utils import matches_any, normalize_text

logger = logging.getLogger(__name__)

RESEARCH_PHRASES: tuple[str, ...] = (
    "compare",
    "versus",
    " vs ",
    "research",
    "latest",
    "document",
    "pdf",
    "documentation",
    "according to",
    "cite",
    "source",
)


class ResearchSpecialist:
    name = "research"

    def run(self, query: str, intent: Intent | None) -> AgentResult:
        findings: list[Finding] = []
        citations: list[Citation] = []
        warnings: list[str] = []
        confidence = 0.4

        if intent and intent.primary_route in {"web", "pdf", "notes", "code"}:
            confidence = 0.65

        try:
            from pdf.retriever import search_documents

            pdf_hits = search_documents(query, top_k=3)
            for hit in pdf_hits:
                content = hit.get("content") or hit.get("document") or str(hit)
                findings.append(
                    Finding(summary=str(content)[:400], source="pdf", topic="document")
                )
            if pdf_hits:
                confidence = max(confidence, 0.72)
                citations.append(Citation(source="pdf", label="Indexed PDFs"))
        except Exception as exc:
            logger.debug("Research specialist PDF search failed: %s", exc)

        try:
            from codebase.retriever import search_code

            code_hits = search_code(query, top_k=3)
            for hit in code_hits:
                findings.append(
                    Finding(
                        summary=f"{hit.get('path', '')}: {hit.get('content', '')[:280]}",
                        source="code_index",
                        topic="project_knowledge",
                    )
                )
            if code_hits:
                confidence = max(confidence, 0.7)
                citations.append(Citation(source="code", label="Indexed repository code"))
        except Exception as exc:
            logger.debug("Research specialist code search failed: %s", exc)

        try:
            from plugins.manager import supervisor_may_use_plugin
            from plugins.permissions import Permission
            from web.retriever import retrieve_web_context_with_stats

            if not supervisor_may_use_plugin(
                "builtin.web", Permission.INTERNET, action="web_retrieval"
            ):
                warnings.append("Web plugin lacks internet permission.")
            else:
                web_text, stats = retrieve_web_context_with_stats(query, max_pages=3)
                if web_text.strip():
                    findings.append(
                        Finding(
                            summary=web_text[:800],
                            source="web",
                            topic="web_research",
                        )
                    )
                    pages = int(stats.get("pages_retrieved", 0))
                    confidence = max(confidence, clamp_confidence(0.55 + 0.1 * pages))
                    citations.append(Citation(source="web", label="Web retrieval"))
        except Exception as exc:
            logger.debug("Research specialist web retrieval failed: %s", exc)
            if not warnings:
                warnings.append("Web retrieval unavailable or returned no results.")

        if not findings:
            warnings.append("No research sources returned content for this query.")

        return AgentResult(
            agent=self.name,
            confidence=clamp_confidence(confidence),
            findings=findings,
            citations=citations,
            warnings=warnings,
        )


def research_specialist_relevant(query: str, intent: Intent | None) -> bool:
    normalized = normalize_text(query)
    if intent and intent.primary_route in {"web", "pdf"}:
        return True
    if intent and intent.type.value in {"comparison", "web", "pdf", "multi_tool"}:
        return True
    return matches_any(normalized, RESEARCH_PHRASES)
