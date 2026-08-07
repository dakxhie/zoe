"""Context building and retrieval for Zoe AI chat.

Heavy retrievers (notes/memory/PDF/code) are imported lazily inside their
call sites so importing this module does not pull Chroma/embedder stacks at
startup. Runtime retrieval behavior is unchanged.
"""

from __future__ import annotations

import logging
import re

from core.chroma import collection_count
from core.index_status import EMPTY_INDEX_MESSAGES, TOOL_COLLECTIONS
from tools.router import route_query

logger = logging.getLogger(__name__)

MEMORY_ACKNOWLEDGEMENT = "Got it. I'll remember that."
NOTES_HEADING = "========================\nPersonal Notes\n========================"
MEMORIES_HEADING = "========================\nLearned Memories\n========================"
PDF_HEADING = "========================\nPDF Documents\n========================"
CODE_HEADING = "========================\nCode\n========================"
WEB_HEADING = "## Web Context"
WEB_SOURCE_INSTRUCTION = (
    "The following information was retrieved from recent web sources.\n"
    "Prefer these sources when answering.\n"
    "If the answer is not contained in the retrieved content,\n"
    "state that the information was not found."
)
WEB_DISAGREEMENT_INSTRUCTION = (
    "When sources disagree, include all retrieved evidence and do not invent a consensus."
)
VISION_HEADING = "## Vision Context"
CONVERSATION_HEADING = (
    "========================\n"
    "Conversation History\n"
    "========================"
)

# Compiled once: web context formatting is stable and parsed on every web turn.
_WEB_SOURCE_PATTERN = re.compile(
    r"Source:\n(.*?)\n\nURL:\n(.*?)(?:\n\nRetrieved:|\Z)",
    re.DOTALL,
)

MAX_CONTEXT_CHARS = 6000
MAX_ITEM_CHARS = 1500


def _log_turn_debug(
    *,
    route: str,
    retriever: str,
    chunks: int,
    context_chars: int,
    analysis_enabled: bool,
    vision: bool,
    web: bool,
    memory_matches: int,
    prompt_chars: int,
) -> None:
    """Log retrieval details for one chat turn at DEBUG level."""
    if not logger.isEnabledFor(logging.DEBUG):
        return

    logger.debug("Route selected: %s", route)
    logger.debug("Retriever used: %s", retriever)
    logger.debug("Chunks returned: %s", chunks)
    logger.debug("Context characters: %s", context_chars)
    logger.debug("Analysis enabled: %s", "yes" if analysis_enabled else "no")
    logger.debug("Vision enabled: %s", "yes" if vision else "no")
    logger.debug("Web enabled: %s", "yes" if web else "no")
    logger.debug("Memory matches: %s", memory_matches)
    logger.debug("Prompt characters: %s", prompt_chars)


def _retrieve_conversation(user_prompt: str) -> str:
    """Retrieve searchable conversation context when history exists."""
    try:
        from conversation.history import history_exists, load_history
        from conversation.retriever import retrieve_conversation_context
        from conversation.summarizer import load_summary, summary_as_text

        if not history_exists():
            return ""

        recent_messages = load_history()[-20:]
        return retrieve_conversation_context(
            user_prompt,
            summary_text=summary_as_text(load_summary()),
            recent_messages=recent_messages,
        )
    except Exception as exc:
        logger.warning("Conversation retrieval failed: %s", exc)
        return ""


def _merge_conversation_context(user_prompt: str, routed_context: str) -> str:
    """Prepend conversation context before routed retrieval context."""
    conversation_context = _retrieve_conversation(user_prompt)
    if not conversation_context.strip():
        return routed_context

    conversation_block = f"{CONVERSATION_HEADING}\n\n{conversation_context}"
    if routed_context.strip():
        return f"{conversation_block}\n\n{routed_context}"
    return conversation_block


def _empty_index_message(tool: str) -> str | None:
    """Return a user-facing message when the routed index is empty."""
    collection_name = TOOL_COLLECTIONS.get(tool)
    if collection_name is None:
        return None

    if collection_count(collection_name) == 0:
        return EMPTY_INDEX_MESSAGES[tool]

    return None


def get_empty_index_response(
    user_prompt: str,
    selected_route: str | None = None,
) -> str | None:
    """Return a direct empty-index response when the routed index has no data."""
    tool = selected_route or route_query(user_prompt)
    return _empty_index_message(tool)


def _retrieve_notes(user_prompt: str, top_k: int = 3) -> list[dict[str, str]]:
    """Retrieve relevant personal notes from the RAG index."""
    try:
        from rag.retriever import search

        return search(user_prompt, top_k=top_k)
    except Exception as exc:
        logger.warning("Notes retrieval failed: %s", exc)
        return []


def _retrieve_memories(user_prompt: str, top_k: int = 3) -> list[dict[str, str]]:
    """Retrieve relevant learned conversation memories."""
    try:
        from memory.retriever import search_memories

        return search_memories(user_prompt, top_k=top_k)
    except Exception as exc:
        logger.warning("Memory retrieval failed: %s", exc)
        return []


def _retrieve_documents(user_prompt: str, top_k: int = 5) -> list[dict[str, str | int]]:
    """Retrieve relevant PDF document chunks."""
    try:
        from pdf.retriever import search_documents

        return search_documents(user_prompt, top_k=top_k)
    except Exception as exc:
        logger.warning("PDF retrieval failed: %s", exc)
        return []


def _retrieve_code(user_prompt: str, top_k: int = 5) -> list[dict[str, str]]:
    """Retrieve relevant indexed code chunks."""
    try:
        from codebase.retriever import search_code

        return search_code(user_prompt, top_k=top_k)
    except Exception as exc:
        logger.warning("Code retrieval failed: %s", exc)
        return []


def _retrieve_vision(image_path: str, prompt: str = "") -> dict[str, str | dict[str, str | int]]:
    """Retrieve vision context for an image file."""
    try:
        from vision.pipeline import analyze_image

        return analyze_image(image_path, prompt=prompt)
    except Exception as exc:
        logger.warning("Vision retrieval failed: %s", exc)
        return {
            "caption": "",
            "ocr": "",
            "combined_context": "",
            "metadata": {
                "filename": image_path,
                "width": 0,
                "height": 0,
                "mode": "",
                "format": "",
            },
        }


def build_vision_context(result: dict[str, str | dict[str, str | int]]) -> str:
    """Format vision analysis output for prompt injection."""
    metadata = result.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    caption = str(result.get("caption", "")).strip()
    ocr = str(result.get("ocr", "")).strip()
    combined = str(result.get("combined_context", "")).strip()

    if not combined and not caption and not ocr:
        return ""

    if not combined:
        combined = (
            f"Image Description:\n\n{caption}\n\n"
            f"Extracted Text:\n\n{ocr}"
        ).strip()

    metadata_lines = [
        f"filename: {metadata.get('filename', '')}",
        f"width: {metadata.get('width', 0)}",
        f"height: {metadata.get('height', 0)}",
        f"mode: {metadata.get('mode', '')}",
        f"format: {metadata.get('format', '')}",
    ]

    return f"{combined}\n\nMetadata:\n" + "\n".join(metadata_lines)


def _retrieve_web(user_prompt: str, max_pages: int = 3) -> tuple[str, dict[str, int]]:
    """Retrieve cached or freshly downloaded web context for the given query."""
    try:
        from web.retriever import retrieve_web_context_with_stats

        return retrieve_web_context_with_stats(user_prompt, max_pages=max_pages)
    except Exception as exc:
        logger.warning("Web retrieval failed: %s", exc)
        return "", {"pages_retrieved": 0, "cache_hits": 0, "downloads": 0}


def _extract_web_sources(web_content: str) -> list[tuple[str, str]]:
    """Extract unique web source titles and URLs from formatted context."""
    sources: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    for match in _WEB_SOURCE_PATTERN.finditer(web_content):
        title = match.group(1).strip()
        url = match.group(2).strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        sources.append((title or url, url))

    return sources


def build_web_sources_footer(sources: list[tuple[str, str]]) -> str:
    """Build a deduplicated source footer for web prompt context."""
    if not sources:
        return ""

    lines = ["Sources:"]
    seen_urls: set[str] = set()
    for title, url in sources:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        lines.append(f"• {title} — {url}")
    return "\n".join(lines)


def _prepare_web_context(user_prompt: str) -> tuple[str, dict[str, int]]:
    """Retrieve web context and append a source footer when pages are available."""
    raw_context, stats = _retrieve_web(user_prompt)
    if not raw_context:
        return "", stats

    sources = _extract_web_sources(raw_context)
    footer = build_web_sources_footer(sources)
    if footer:
        return f"{raw_context}\n\n{footer}", stats

    return raw_context, stats


def _truncate_at_paragraph_boundary(text: str, limit: int) -> str:
    """Truncate long text at paragraph or sentence boundaries when possible."""
    if len(text) <= limit:
        return text

    chunk = text[:limit]
    paragraph_break = chunk.rfind("\n\n")
    if paragraph_break >= int(limit * 0.5):
        return chunk[:paragraph_break].rstrip()

    sentence_break = max(chunk.rfind(". "), chunk.rfind(".\n"), chunk.rfind("\n"))
    if sentence_break >= int(limit * 0.5):
        end = sentence_break + 1 if chunk[sentence_break : sentence_break + 1] == "." else sentence_break
        return chunk[:end].rstrip()

    return chunk.rstrip() + "..."


def _log_web_retrieval(web_content: str, stats: dict[str, int]) -> None:
    """Log web retrieval details when logging is enabled."""
    if not logger.isEnabledFor(logging.INFO):
        return

    logger.info("Route selected: web")
    logger.info("Number of pages retrieved: %s", stats.get("pages_retrieved", 0))
    logger.info("Cache hits: %s", stats.get("cache_hits", 0))
    logger.info("Total web context size: %s characters", len(web_content))


def _truncate_text(text: str, limit: int) -> str:
    """Truncate long context text safely."""
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _join_content(items: list[dict[str, str | int]]) -> str:
    """Join retrieved document content into one bounded text block."""
    if not items:
        return ""

    parts = [_truncate_text(str(item["content"]), MAX_ITEM_CHARS) for item in items]
    joined = "\n\n".join(part for part in parts if part)

    remaining = MAX_CONTEXT_CHARS
    bounded_parts: list[str] = []

    for part in parts:
        if remaining <= 0:
            break
        if len(part) <= remaining:
            bounded_parts.append(part)
            remaining -= len(part) + 2
            continue
        bounded_parts.append(_truncate_text(part, remaining))
        break

    return "\n\n".join(bounded_parts) if bounded_parts else _truncate_text(joined, MAX_CONTEXT_CHARS)


def _append_section(sections: list[str], heading: str, content: str) -> None:
    """Append one context section when content is available."""
    if not content.strip():
        return
    sections.append(f"{heading}\n\n{content}")


def _retrieve_for_tool(tool: str, user_prompt: str) -> list[dict[str, str | int]]:
    """Retrieve context from the tool selected by the router."""
    if tool == "memory":
        return _retrieve_memories(user_prompt, top_k=3)
    if tool == "notes":
        return _retrieve_notes(user_prompt, top_k=3)
    if tool == "pdf":
        return _retrieve_documents(user_prompt, top_k=5)
    if tool == "code":
        return _retrieve_code(user_prompt, top_k=5)
    return []


def _heading_for_tool(tool: str) -> str | None:
    """Return the context heading for a routed tool."""
    headings = {
        "memory": MEMORIES_HEADING,
        "notes": NOTES_HEADING,
        "pdf": PDF_HEADING,
        "code": CODE_HEADING,
        "web": WEB_HEADING,
        "vision": VISION_HEADING,
    }
    return headings.get(tool)


def _build_merged_context(
    user_prompt: str,
    selected_route: str | None = None,
) -> str:
    """Build context from the single retrieval source selected by the tool router."""
    tool = selected_route or route_query(user_prompt)
    logger.debug("Routed query to tool: %s", tool)

    if tool in {"chat", "web", "vision"}:
        return ""

    results = _retrieve_for_tool(tool, user_prompt)
    if not results:
        empty_message = _empty_index_message(tool)
        if empty_message is not None:
            return empty_message
        return ""

    heading = _heading_for_tool(tool)
    if not heading:
        return ""

    sections: list[str] = []
    _append_section(sections, heading, _join_content(results))

    merged = "\n\n".join(sections)
    return _truncate_text(merged, MAX_CONTEXT_CHARS)


def _count_retrieved_chunks(user_prompt: str, selected_route: str | None = None) -> int:
    """Return the number of retrieved chunks for debug logging."""
    tool = selected_route or route_query(user_prompt)
    if tool in {"chat", "web", "vision"}:
        return 0
    return len(_retrieve_for_tool(tool, user_prompt))


def _build_analysis_system_content(context: str) -> str:
    """Build the system prompt for project analysis using gathered context."""
    return (
        "You are Zoe.\n"
        "The user asked for a project analysis.\n"
        "Answer using ONLY the provided project analysis context below.\n"
        "Do not ask the user for more files, code, or project details.\n"
        "Summarize the architecture and recommend concrete improvements.\n\n"
        f"Context:\n{context}"
    )


def _build_web_system_content(context: str) -> str:
    """Build the system prompt for answers grounded in retrieved web sources."""
    return (
        "You are Zoe.\n"
        f"{WEB_SOURCE_INSTRUCTION}\n"
        f"{WEB_DISAGREEMENT_INSTRUCTION}\n\n"
        f"Context:\n{WEB_HEADING}\n\n{context}"
    )


def _build_vision_system_content(context: str) -> str:
    """Build the system prompt for answers grounded in vision context."""
    return (
        "You are Zoe.\n"
        "Answer using the provided vision context about the user's image.\n"
        "Prefer the image description and extracted text when answering.\n"
        "If the answer is not contained in the vision context, "
        "state that the information was not found.\n\n"
        f"Context:\n{VISION_HEADING}\n\n{context}"
    )


def _build_system_content(context: str) -> str:
    """Build the system prompt containing Zoe instructions and retrieved context."""
    base = (
        "You are Zoe.\n"
        "Answer using the provided context whenever possible.\n"
        "If the answer is not in the context, answer normally."
    )

    if not context:
        return base

    return f"{base}\n\nContext:\n{context}"


def _build_chat_messages(
    user_question: str,
    history: list[dict[str, str]],
    analysis_context: str = "",
    vision_context: str = "",
    selected_route: str | None = None,
    agent_context: str = "",
) -> list[dict[str, str]]:
    """Build chat messages with system context, history, and the current user turn."""
    tool = selected_route or route_query(user_question)
    chunks = 0
    context_chars = 0
    memory_matches = 0
    web_enabled = False
    vision_enabled = bool(vision_context.strip())
    analysis_enabled = bool(analysis_context.strip())

    if analysis_enabled:
        context = _truncate_text(analysis_context, MAX_CONTEXT_CHARS)
        system_content = _build_analysis_system_content(context)
        context_chars = len(context)
        chunks = 1
        logger.info("Injecting analysis context (%s chars)", context_chars)
    elif vision_enabled:
        context = _truncate_at_paragraph_boundary(vision_context, MAX_CONTEXT_CHARS)
        system_content = _build_vision_system_content(context)
        context_chars = len(context)
        chunks = 1
    elif agent_context.strip():
        context = _truncate_text(agent_context, MAX_CONTEXT_CHARS)
        context_chars = len(context)
        chunks = max(1, context.count("========================") + context.count("##"))
        system_content = _build_system_content(context)
        if tool == "memory":
            memory_matches = chunks
    elif tool == "web":
        web_context, stats = _prepare_web_context(user_question)
        web_enabled = bool(web_context)
        if web_context:
            truncated_context = _truncate_at_paragraph_boundary(
                web_context,
                MAX_CONTEXT_CHARS,
            )
            _log_web_retrieval(truncated_context, stats)
            merged_context = _merge_conversation_context(user_question, truncated_context)
            system_content = _build_web_system_content(merged_context)
            context_chars = len(merged_context)
            chunks = stats.get("pages_retrieved", 0)
        else:
            logger.info(
                "Web route selected but retrieval returned empty; "
                "falling back to normal chat generation"
            )
            system_content = _build_system_content(_merge_conversation_context(user_question, ""))
    else:
        context = _build_merged_context(user_question, selected_route=tool)
        context = _merge_conversation_context(user_question, context)
        context_chars = len(context)
        chunks = _count_retrieved_chunks(user_question, selected_route=tool)
        if tool == "memory":
            memory_matches = chunks
        system_content = _build_system_content(context)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_content},
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_question})

    _log_turn_debug(
        route=tool,
        retriever=tool,
        chunks=chunks,
        context_chars=context_chars,
        analysis_enabled=analysis_enabled,
        vision=vision_enabled,
        web=web_enabled,
        memory_matches=memory_matches,
        prompt_chars=len(system_content),
    )
    return messages
