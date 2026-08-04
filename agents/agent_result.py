"""Structured results exchanged between specialist agents."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Citation:
    """A source reference attached to specialist findings."""

    source: str
    label: str
    url: str = ""


@dataclass(frozen=True)
class Finding:
    """One structured insight from a specialist agent."""

    summary: str
    detail: str = ""
    source: str = ""
    topic: str = ""


@dataclass
class AgentResult:
    """Output from one specialist agent (never shown raw to the user)."""

    agent: str
    confidence: float
    findings: list[Finding] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def context_block(self) -> str:
        """Format findings for LLM context injection."""
        if not self.findings and not self.warnings:
            return ""
        lines = [f"### {self.agent.title()} Specialist (confidence {self.confidence:.2f})"]
        for item in self.findings:
            lines.append(f"- {item.summary}")
            if item.detail:
                lines.append(f"  {item.detail}")
        for warning in self.warnings:
            lines.append(f"- Warning: {warning}")
        for cite in self.citations:
            label = cite.label or cite.source
            if cite.url:
                lines.append(f"- Source: {label} ({cite.url})")
            else:
                lines.append(f"- Source: {label}")
        return "\n".join(lines)


@dataclass(frozen=True)
class SupervisorDecision:
    """Internal supervisor routing decision (DEBUG only)."""

    query: str
    selected_agents: tuple[str, ...]
    skipped_reason: str = ""


@dataclass
class SupervisorBrief:
    """Merged specialist output for the orchestrator."""

    context: str
    results: list[AgentResult]
    decision: SupervisorDecision
    clarification: str = ""
