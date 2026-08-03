"""Chat request pipeline for Zoe AI."""

from __future__ import annotations

import logging
import time

from memory.history import add_message, get_history
from memory.store import save_memory
from tools.executor import execute_tool

from brain.context import (
    MEMORY_ACKNOWLEDGEMENT,
    _build_chat_messages,
    _log_turn_debug,
    _retrieve_vision,
    build_vision_context,
)
from brain.generation import generate_text, load_model
from tools.router import extract_image_path

logger = logging.getLogger(__name__)


def _record_exchange(user_prompt: str, assistant_reply: str) -> None:
    """Store one completed user and assistant exchange."""
    add_message("user", user_prompt)
    add_message("assistant", assistant_reply)


def _prepare_chat_session() -> None:
    """Initialize a chat session and restore prior history when available."""
    from conversation.history import history_exists, restore_message_cache
    from conversation.session import create_session

    create_session()
    restore_message_cache()
    if history_exists():
        print("✓ Previous conversation restored")
    else:
        print("✓ Starting new conversation")


def _try_save_memory(text: str) -> bool:
    """Attempt to store a conversation memory without interrupting chat."""
    try:
        return save_memory(text)
    except Exception as exc:
        logger.warning("Memory save failed: %s", exc)
        return False


def generate_image_response(
    image_path: str,
    prompt: str = "",
    max_new_tokens: int = 256,
) -> str:
    """Generate an assistant reply about an image."""
    vision_result = _retrieve_vision(image_path, prompt=prompt)
    metadata = vision_result.get("metadata", {})
    if not isinstance(metadata, dict) or metadata.get("width", 0) == 0:
        return f"Sorry, I could not load the image: {image_path}"

    vision_context = build_vision_context(vision_result)
    if not vision_context.strip():
        return f"Sorry, I could not extract any information from the image: {image_path}"

    loaded_tokenizer, loaded_model = load_model()
    history = get_history(max_messages=20)
    user_question = prompt.strip() or "Describe this image."
    messages = _build_chat_messages(
        user_question,
        history,
        vision_context=vision_context,
        selected_route="vision",
    )
    _log_turn_debug(
        route="vision",
        retriever="vision",
        chunks=1,
        context_chars=len(vision_context),
        analysis_enabled=False,
        vision=True,
        web=False,
        memory_matches=0,
        prompt_chars=len(messages[0]["content"]),
    )
    reply = generate_text(
        loaded_tokenizer,
        loaded_model,
        messages,
        max_new_tokens=max_new_tokens,
    )
    _record_exchange(user_question, reply)
    return reply


def generate_response(prompt: str, max_new_tokens: int = 256) -> str:
    """Generate an assistant reply for the given user prompt."""
    if _try_save_memory(prompt):
        reply = MEMORY_ACKNOWLEDGEMENT
        _record_exchange(prompt, reply)
        return reply

    handled, tool_result = execute_tool(prompt)
    if handled:
        _record_exchange(prompt, tool_result)
        return tool_result

    from agents.orchestrator import orchestrate_chat_turn

    generation_start = time.perf_counter()
    turn = orchestrate_chat_turn(prompt)

    if turn.use_vision_path:
        image_path = turn.use_vision_path
        return generate_image_response(image_path, prompt, max_new_tokens=max_new_tokens)

    if turn.direct_reply is not None:
        _record_exchange(prompt, turn.direct_reply)
        return turn.direct_reply

    if turn.empty_index_response is not None:
        _record_exchange(prompt, turn.empty_index_response)
        return turn.empty_index_response

    if turn.messages is None:
        from tools.router import route_query

        loaded_tokenizer, loaded_model = load_model()
        history = get_history(max_messages=20)
        messages = _build_chat_messages(prompt, history, selected_route=route_query(prompt))
    else:
        loaded_tokenizer, loaded_model = load_model()
        messages = turn.messages

    if turn.state and turn.state.analysis_context.strip() and "Project Analysis" not in messages[0]["content"]:
        logger.warning("Analysis context was not injected into the system prompt")

    if logger.isEnabledFor(logging.DEBUG) and turn.state:
        turn.state.timings.generation_ms = (time.perf_counter() - generation_start) * 1000
        logger.debug("Generation time ms: %.1f", turn.state.timings.generation_ms)

    reply = generate_text(
        loaded_tokenizer,
        loaded_model,
        messages,
        max_new_tokens=max_new_tokens,
    )
    _record_exchange(prompt, reply)
    return reply
