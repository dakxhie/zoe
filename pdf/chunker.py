"""Text chunking utilities for PDF documents."""

from __future__ import annotations

from typing import TypedDict


class TextChunk(TypedDict):
    """A deterministic text chunk extracted from a document."""

    chunk_id: str
    text: str


def _split_by_words(text: str, chunk_size: int) -> list[str]:
    """Split long text at word boundaries without exceeding chunk_size."""
    words = text.split()
    if not words:
        return []

    parts: list[str] = []
    current_words: list[str] = []
    current_length = 0

    for word in words:
        separator_length = 1 if current_words else 0
        addition_length = separator_length + len(word)

        if current_length + addition_length > chunk_size and current_words:
            parts.append(" ".join(current_words))
            current_words = [word]
            current_length = len(word)
            continue

        current_words.append(word)
        current_length += addition_length

    if current_words:
        parts.append(" ".join(current_words))

    return parts


def _paragraph_units(text: str, chunk_size: int) -> list[str]:
    """Break text into paragraph-preserving units."""
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    units: list[str] = []

    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size:
            units.append(paragraph)
            continue
        units.extend(_split_by_words(paragraph, chunk_size))

    return units


def _overlap_prefix(previous_chunk: str, overlap: int) -> str:
    """Return the overlapping prefix from the previous chunk at a word boundary."""
    if overlap <= 0:
        return ""

    if len(previous_chunk) <= overlap:
        return previous_chunk

    overlap_text = previous_chunk[-overlap:]
    space_index = overlap_text.find(" ")
    if space_index == -1:
        return overlap_text

    return overlap_text[space_index + 1 :]


def _build_raw_chunks(units: list[str], chunk_size: int) -> list[str]:
    """Pack paragraph units into initial chunks without overlap."""
    raw_chunks: list[str] = []
    current_parts: list[str] = []
    current_length = 0

    def flush_current() -> None:
        nonlocal current_parts, current_length
        if not current_parts:
            return
        raw_chunks.append("\n\n".join(current_parts))
        current_parts = []
        current_length = 0

    for unit in units:
        separator_length = 2 if current_parts else 0
        projected_length = current_length + separator_length + len(unit)

        if projected_length <= chunk_size:
            current_parts.append(unit)
            current_length = projected_length
            continue

        flush_current()
        current_parts = [unit]
        current_length = len(unit)

    flush_current()
    return raw_chunks


def _apply_overlap(raw_chunks: list[str], overlap: int) -> list[str]:
    """Apply overlap between consecutive chunks."""
    if not raw_chunks:
        return []

    overlapped_chunks = [raw_chunks[0]]

    for chunk in raw_chunks[1:]:
        prefix = _overlap_prefix(overlapped_chunks[-1], overlap)
        if prefix:
            overlapped_chunks.append(f"{prefix}\n\n{chunk}")
        else:
            overlapped_chunks.append(chunk)

    return overlapped_chunks


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[TextChunk]:
    """Split text into overlapping chunks while preserving paragraphs and words."""
    normalized = text.strip()
    if not normalized:
        return []

    units = _paragraph_units(normalized, chunk_size)
    if not units:
        return []

    raw_chunks = _build_raw_chunks(units, chunk_size)
    final_chunks = _apply_overlap(raw_chunks, overlap)

    return [
        {"chunk_id": f"chunk_{index:04d}", "text": chunk}
        for index, chunk in enumerate(final_chunks)
        if chunk.strip()
    ]
