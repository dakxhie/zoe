"""Chat request pipeline for Zoe AI."""

from __future__ import annotations

import logging

from agents.analyzer import run_project_analysis
from memory.history import add_message, get_history
from memory.store import save_memory
from tools.executor import execute_tool

from brain.context import MEMORY_ACKNOWLEDGEMENT, _build_chat_messages, get_empty_index_response
from brain.generation import generate_text, load_model

logger = logging.getLogger(__name__)


def _record_exchange(user_prompt: str, assistant_reply: str) -> None:
    """Store one completed user and assistant exchange."""
    add_message("user", user_prompt)
    add_message("assistant", assistant_reply)


def _try_save_memory(text: str) -> bool:
    """Attempt to store a conversation memory without interrupting chat."""
    try:
        return save_memory(text)
    except Exception as exc:
        logger.warning("Memory save failed: %s", exc)
        return False


def generate_response(prompt: str, max_new_tokens: int = 256) -> str:
    """Generate an assistant reply for the given user prompt."""
    # Memory storage injection: save personal messages before generation.
    if _try_save_memory(prompt):
        reply = MEMORY_ACKNOWLEDGEMENT
        _record_exchange(prompt, reply)
        return reply

    handled, tool_result = execute_tool(prompt)
    if handled:
        _record_exchange(prompt, tool_result)
        return tool_result

    is_analysis, analysis_context = run_project_analysis(prompt)

    if not is_analysis:
        empty_index_response = get_empty_index_response(prompt)
        if empty_index_response is not None:
            _record_exchange(prompt, empty_index_response)
            return empty_index_response

    loaded_tokenizer, loaded_model = load_model()

    history = get_history()
    messages = _build_chat_messages(
        prompt,
        history,
        analysis_context=analysis_context if is_analysis else "",
    )
    reply = generate_text(
        loaded_tokenizer,
        loaded_model,
        messages,
        max_new_tokens=max_new_tokens,
    )
    _record_exchange(prompt, reply)
    return reply
