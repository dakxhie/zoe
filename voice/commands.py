"""Local voice commands that bypass the LLM when possible."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from core.text_utils import normalize_text
from tools.executor import execute_tool

logger = logging.getLogger(__name__)


class VoiceAction(str, Enum):
    """Desktop actions triggered by voice."""

    OPEN_SETTINGS = "open_settings"
    CLEAR_CHAT = "clear_chat"
    RUN_DOCTOR = "run_doctor"
    INDEX_PDFS = "index_pdfs"
    INDEX_NOTES = "index_notes"
    ANALYZE_PROJECT = "analyze_project"


@dataclass(frozen=True)
class CommandResult:
    """Outcome of a voice command attempt."""

    handled: bool
    response: str = ""
    action: VoiceAction | None = None


def _match(text: str, phrases: tuple[str, ...]) -> bool:
    normalized = normalize_text(text)
    return any(phrase in normalized for phrase in phrases)


def try_voice_command(text: str) -> CommandResult:
    """Handle local commands and lightweight tools without LLM generation."""
    normalized = normalize_text(text)
    if not normalized:
        return CommandResult(handled=False)

    if _match(normalized, ("what are you doing", "task status", "current task", "progress")):
        from agents.tasks.task_manager import get_idle_status

        return CommandResult(True, get_idle_status())

    if _match(normalized, ("open settings", "show settings")):
        return CommandResult(True, "Opening settings.", VoiceAction.OPEN_SETTINGS)
    if _match(normalized, ("clear chat", "clear conversation")):
        return CommandResult(True, "Chat cleared.", VoiceAction.CLEAR_CHAT)
    if _match(normalized, ("run doctor", "system doctor", "health check")):
        return CommandResult(True, "Running system doctor.", VoiceAction.RUN_DOCTOR)
    if _match(normalized, ("index pdfs", "index pdf", "reindex pdfs")):
        return CommandResult(True, "Indexing PDFs.", VoiceAction.INDEX_PDFS)
    if _match(normalized, ("index notes", "reindex notes")):
        return CommandResult(True, "Indexing notes.", VoiceAction.INDEX_NOTES)
    if _match(normalized, ("analyze project", "analyze this project", "project analysis")):
        return CommandResult(True, "Starting project analysis.", VoiceAction.ANALYZE_PROJECT)

    handled, tool_result = execute_tool(text)
    if handled and tool_result:
        logger.debug("Voice command handled by tools.executor")
        return CommandResult(True, tool_result)

    return CommandResult(handled=False)


def generate_voice_response(text: str) -> str:
    """Generate a response using the same chat pipeline as desktop/CLI."""
    from brain.pipeline import generate_response

    return generate_response(text)
