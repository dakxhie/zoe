"""Chat request pipeline for Zoe AI."""

from __future__ import annotations

import logging

from agents.analyzer import run_project_analysis
from memory.history import add_message, get_history
from memory.store import save_memory
from tools.executor import execute_tool

from brain.context import (
    MEMORY_ACKNOWLEDGEMENT,
    _build_chat_messages,
    _log_turn_debug,
    _retrieve_vision,
    build_vision_context,
    get_empty_index_response,
)
from brain.generation import generate_text, load_model
from tools.router import extract_image_path, route_query

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

    is_analysis, analysis_context = run_project_analysis(prompt)
    selected_route = route_query(prompt)

    if selected_route == "vision":
        image_path = extract_image_path(prompt)
        if not image_path:
            reply = "Please include a supported image file path in your request."
            _record_exchange(prompt, reply)
            return reply
        return generate_image_response(image_path, prompt, max_new_tokens=max_new_tokens)

    if is_analysis and not analysis_context.strip():
        logger.warning("Analysis enabled but context is empty; continuing without analysis injection")

    if not is_analysis:
        empty_index_response = get_empty_index_response(prompt, selected_route)
        if empty_index_response is not None:
            _record_exchange(prompt, empty_index_response)
            return empty_index_response

    loaded_tokenizer, loaded_model = load_model()

    history = get_history(max_messages=20)
    effective_analysis_context = analysis_context if is_analysis else ""
    messages = _build_chat_messages(
        prompt,
        history,
        analysis_context=effective_analysis_context,
        selected_route=selected_route,
    )

    system_content = messages[0]["content"]
    logger.info("Prompt chars: %s", len(system_content))
    if is_analysis:
        logger.info("Analysis enabled: yes")
        if "Project Analysis" not in system_content:
            logger.warning("Analysis context was not injected into the system prompt")

    reply = generate_text(
        loaded_tokenizer,
        loaded_model,
        messages,
        max_new_tokens=max_new_tokens,
    )
    _record_exchange(prompt, reply)
    return reply
