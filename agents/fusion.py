"""Retrieval fusion and context ranking for Zoe AI."""

from __future__ import annotations

import hashlib
import logging

from agents.state import ToolOutput

logger = logging.getLogger(__name__)

TOOL_PRIORITY: tuple[str, ...] = (
    "memory",
    "conversation",
    "notes",
    "pdf",
    "code",
    "vision",
    "web",
    "project_analysis",
)

SECTION_HEADINGS: dict[str, str] = {
    "memory": "========================\nLearned Memories\n========================",
    "conversation": "========================\nConversation History\n========================",
    "notes": "========================\nPersonal Notes\n========================",
    "pdf": "========================\nPDF Documents\n========================",
    "code": "========================\nCode\n========================",
    "vision": "## Vision Context",
    "web": "## Web Context",
    "project_analysis": "========================\nProject Analysis\n========================",
}

MAX_FUSED_CHARS = 6000
MAX_SECTION_CHARS = 1500


def _section_key(text: str) -> str:
    """Hash normalized section text for deduplication."""
    normalized = " ".join(text.split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def fuse_tool_outputs(outputs: list[ToolOutput], *, max_chars: int = MAX_FUSED_CHARS) -> str:
    """Rank, deduplicate, and trim tool outputs into one context block."""
    if not outputs:
        return ""

    ranked = sorted(
        outputs,
        key=lambda item: (
            TOOL_PRIORITY.index(item.tool) if item.tool in TOOL_PRIORITY else len(TOOL_PRIORITY),
            -item.confidence,
        ),
    )

    sections: list[str] = []
    seen: set[str] = set()
    remaining = max_chars

    for output in ranked:
        content = output.content.strip()
        if not content or not output.success:
            continue

        key = _section_key(content)
        if key in seen:
            logger.debug("Fusion skipped duplicate section from %s", output.tool)
            continue
        seen.add(key)

        heading = SECTION_HEADINGS.get(output.tool, f"## {output.tool.title()}")
        section_body = _truncate(content, min(MAX_SECTION_CHARS, remaining))
        if not section_body:
            continue

        section = f"{heading}\n\n{section_body}"
        if len(section) > remaining:
            section = _truncate(section, remaining)
        if not section.strip():
            continue

        sections.append(section)
        remaining -= len(section) + 2
        if remaining <= 0:
            break

    fused = "\n\n".join(sections)
    logger.debug("Fused context: %s sections, %s chars", len(sections), len(fused))
    return fused
