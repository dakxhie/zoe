"""Shared indexing helpers for Zoe AI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

ChunkType = TypeVar("ChunkType")


def prepare_new_chunks(
    chunks: list[ChunkType],
    make_storage_id: Callable[[int, ChunkType], str],
    known_ids: set[str],
    known_texts: set[str],
    get_text: Callable[[ChunkType], str],
) -> list[tuple[str, ChunkType, int]]:
    """Return chunks that are not already indexed by id or exact text."""
    pending: list[tuple[str, ChunkType, int]] = []

    for chunk_number, chunk in enumerate(chunks):
        chunk_text = get_text(chunk).strip()
        if not chunk_text:
            continue

        if chunk_text in known_texts:
            continue

        storage_id = make_storage_id(chunk_number, chunk)
        if storage_id in known_ids:
            continue

        known_texts.add(chunk_text)
        pending.append((storage_id, chunk, chunk_number))

    return pending
