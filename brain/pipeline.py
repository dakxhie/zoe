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
    _build_system_content,
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
    from tools.tool_loop import guard_legacy_execution

    guard_legacy_execution("brain.pipeline._try_save_memory")  # Phase D: legacy-only
    try:
        return save_memory(text)
    except Exception as exc:
        logger.warning("Memory save failed: %s", exc)
        return False


def _finalize_turn_memory(user_prompt: str, assistant_reply: str) -> None:
    """Run post-turn memory intelligence (scoring, review, reinforcement)."""
    from tools.tool_loop import guard_legacy_execution

    guard_legacy_execution("brain.pipeline._finalize_turn_memory")  # Phase D: legacy-only
    try:
        from agents.orchestrator import finalize_conversation_memory
        from tools.router import route_query

        finalize_conversation_memory(
            user_prompt,
            assistant_reply,
            route_hint=route_query(user_prompt),
        )
    except Exception as exc:
        logger.warning("Finalize turn memory failed: %s", exc)


def _emit_conversation_finished(user_prompt: str, assistant_reply: str) -> None:
    from plugins.events import Event, emit

    emit(
        Event.CONVERSATION_FINISHED,
        {"user_message": user_prompt, "assistant_reply": assistant_reply},
    )


def _complete_turn(user_prompt: str, assistant_reply: str) -> str:
    from plugins.plugin_api import apply_chat_hooks

    reply = apply_chat_hooks(user_prompt, assistant_reply)
    _record_exchange(user_prompt, reply)
    _finalize_turn_memory(user_prompt, reply)
    _emit_conversation_finished(user_prompt, reply)
    try:
        from deployment.telemetry import record_telemetry

        record_telemetry("conversation", {"chars": len(reply)})
    except Exception as exc:
        # Telemetry must never interrupt a completed chat turn.
        logger.debug("Conversation telemetry skipped: %s", exc)
    return reply


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


def _handle_explicit_web_turn(prompt: str, max_new_tokens: int) -> str | None:
    """Handle a turn whose current message explicitly asked for web access (Phase B2).

    Returns ``None`` for every other turn. Non-explicit turns never reach the
    network: the single decision in ``web.policy`` denies them.
    """
    from tools.tool_loop import guard_legacy_execution

    guard_legacy_execution("brain.pipeline._handle_explicit_web_turn")  # Phase D: legacy-only
    from tools.result_envelope import ErrorType
    from web.policy import (
        DIAG_OFFLINE,
        DIAG_QUERY_UNBUILDABLE,
        blocked_notice,
        current_decision,
        decorate_web_reply,
    )

    decision = current_decision()
    if not decision.explicit_intent:
        return None

    if (
        decision.error_type is ErrorType.EGRESS_BLOCKED_SENSITIVE
        or decision.diagnostic == DIAG_QUERY_UNBUILDABLE
    ):
        return _complete_turn(prompt, blocked_notice(decision))

    from brain.context import WEB_NOT_USED_INSTRUCTION

    loaded_tokenizer, loaded_model = load_model()
    history = get_history(max_messages=20)

    if decision.diagnostic == DIAG_OFFLINE:
        messages = _build_chat_messages(prompt, history, selected_route="chat")
        messages[0]["content"] = f"{messages[0]['content']}\n\n{WEB_NOT_USED_INSTRUCTION}"
        reply = generate_text(loaded_tokenizer, loaded_model, messages, max_new_tokens=max_new_tokens)
        return _complete_turn(prompt, f"{blocked_notice(decision)}\n\n{reply}".strip())

    # Authorized: the single web route performs the one gated search for this turn.
    messages = _build_chat_messages(prompt, history, selected_route="web")
    reply = generate_text(loaded_tokenizer, loaded_model, messages, max_new_tokens=max_new_tokens)
    return _complete_turn(prompt, decorate_web_reply(reply))


def generate_response(prompt: str, max_new_tokens: int = 256) -> str:
    """Generate an assistant reply for the given user prompt.

    Phase B2: the web authorization decision is computed once from this prompt
    (the current user message) and discarded when the turn ends.

    Phase D: with ``ZOE_TOOL_LOOP`` ON (default OFF) the turn goes through the
    bounded tool loop, the only execution authority; the legacy path below is
    not called. With the flag OFF the legacy path is unchanged.
    """
    from tools.tool_loop import is_tool_loop_enabled
    from web.policy import web_turn

    with web_turn(prompt):
        if is_tool_loop_enabled():
            return _generate_tool_loop_response(prompt, max_new_tokens=max_new_tokens)
        return _generate_response_for_turn(prompt, max_new_tokens=max_new_tokens)


def _tool_loop_model(max_new_tokens: int):
    """The model callable used by the tool loop (one generation per invocation)."""

    def model_fn(messages: list[dict], tools: list[dict]) -> str:
        loaded_tokenizer, loaded_model = load_model()
        return generate_text(loaded_tokenizer, loaded_model, messages, max_new_tokens=max_new_tokens, tools=tools)

    return model_fn


def _generate_tool_loop_response(prompt: str, max_new_tokens: int = 256) -> str:
    """Phase D turn: system + offered tool schemas + existing history + current message.

    No legacy execution, retrieval or memory paths run here; only the user
    message and the final answer are recorded in the existing history.
    """
    from tools.tool_loop import run_tool_loop

    history = get_history(max_messages=20)
    result = run_tool_loop(
        prompt,
        model_fn=_tool_loop_model(max_new_tokens),
        history=history,
        system_prompt=_build_system_content(""),
    )
    _record_exchange(prompt, result.text)
    return result.text


def _generate_response_for_turn(prompt: str, max_new_tokens: int = 256) -> str:
    """Generate the reply for one user turn (web decision already scoped)."""
    from tools.tool_loop import guard_legacy_execution

    guard_legacy_execution("brain.pipeline._generate_response_for_turn")  # Phase D: legacy-only
    from plugins.events import Event, emit
    from plugins.manager import initialize_plugins

    initialize_plugins()
    emit(Event.CONVERSATION_STARTED, {"user_message": prompt})

    try:
        from memory.intelligence.memory_review import respond_to_profile_query

        profile_reply = respond_to_profile_query(prompt)
        if profile_reply is not None:
            _record_exchange(prompt, profile_reply)
            _emit_conversation_finished(prompt, profile_reply)
            return profile_reply
    except Exception as exc:
        logger.debug("Profile query handling skipped: %s", exc)

    if _try_save_memory(prompt):
        reply = MEMORY_ACKNOWLEDGEMENT
        _record_exchange(prompt, reply)
        _emit_conversation_finished(prompt, reply)
        return reply

    web_reply = _handle_explicit_web_turn(prompt, max_new_tokens)
    if web_reply is not None:
        return web_reply

    handled, tool_result = execute_tool(prompt)
    if handled:
        return _complete_turn(prompt, tool_result)

    from agents.orchestrator import orchestrate_chat_turn

    generation_start = time.perf_counter()
    turn = orchestrate_chat_turn(prompt)

    if turn.use_vision_path:
        image_path = turn.use_vision_path
        return generate_image_response(image_path, prompt, max_new_tokens=max_new_tokens)

    if turn.direct_reply is not None:
        return _complete_turn(prompt, turn.direct_reply)

    if turn.empty_index_response is not None:
        return _complete_turn(prompt, turn.empty_index_response)

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
    return _complete_turn(prompt, reply)
