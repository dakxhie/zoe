"""Hugging Face model loading and chat generation for Zoe AI."""

from __future__ import annotations

from brain.context import (
    CODE_HEADING,
    MAX_CONTEXT_CHARS,
    MAX_ITEM_CHARS,
    MEMORY_ACKNOWLEDGEMENT,
    MEMORIES_HEADING,
    NOTES_HEADING,
    PDF_HEADING,
    _append_section,
    _build_chat_messages,
    _build_merged_context,
    _build_system_content,
    _heading_for_tool,
    _join_content,
    _retrieve_code,
    _retrieve_documents,
    _retrieve_for_tool,
    _retrieve_memories,
    _retrieve_notes,
    _truncate_text,
)
from brain.generation import ModelLoadError, get_model_load_count, is_model_loaded, load_model, model, tokenizer
from brain.pipeline import generate_response

__all__ = [
    "CODE_HEADING",
    "MAX_CONTEXT_CHARS",
    "MAX_ITEM_CHARS",
    "MEMORY_ACKNOWLEDGEMENT",
    "MEMORIES_HEADING",
    "ModelLoadError",
    "NOTES_HEADING",
    "PDF_HEADING",
    "_append_section",
    "_build_chat_messages",
    "_build_merged_context",
    "_build_system_content",
    "_heading_for_tool",
    "_join_content",
    "_retrieve_code",
    "_retrieve_documents",
    "_retrieve_for_tool",
    "_retrieve_memories",
    "_retrieve_notes",
    "_truncate_text",
    "generate_response",
    "get_model_load_count",
    "is_model_loaded",
    "load_model",
    "model",
    "tokenizer",
]
