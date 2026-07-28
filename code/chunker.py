"""Smart code chunking utilities."""

from __future__ import annotations

import ast
import re
from typing import TypedDict

from pdf.chunker import chunk_text

DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 150

JS_CLASS_PATTERN = re.compile(r"^\s*export\s+class\s+\w+", re.MULTILINE)
JS_FUNCTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*export\s+(async\s+)?function\s+\w+", re.MULTILINE),
    re.compile(r"^\s*(async\s+)?function\s+\w+", re.MULTILINE),
    re.compile(r"^\s*const\s+\w+\s*=\s*(async\s*)?\(", re.MULTILINE),
    re.compile(r"^\s*\w+\s*\([^)]*\)\s*\{", re.MULTILINE),
)


class CodeChunk(TypedDict):
    """A code chunk extracted from a source file."""

    chunk_id: str
    text: str
    filename: str
    language: str


def _extract_line_blocks(content: str, start_lines: list[int]) -> list[str]:
    """Split content into blocks starting at the provided line numbers."""
    if not start_lines:
        return []

    lines = content.splitlines()
    unique_starts = sorted(set(start_lines))
    blocks: list[str] = []

    for index, start_line in enumerate(unique_starts):
        start_index = max(start_line - 1, 0)
        end_index = (
            unique_starts[index + 1] - 1
            if index + 1 < len(unique_starts)
            else len(lines)
        )
        block = "\n".join(lines[start_index:end_index]).strip()
        if block:
            blocks.append(block)

    return blocks


def _chunk_python(content: str) -> list[str]:
    """Extract Python classes, functions, and methods."""
    lines = content.splitlines()
    blocks: list[str] = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            end_line = node.end_lineno or node.lineno
            block = "\n".join(lines[node.lineno - 1 : end_line]).strip()
            if block:
                blocks.append(block)

            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_end = child.end_lineno or child.lineno
                    method_block = "\n".join(
                        lines[child.lineno - 1 : method_end]
                    ).strip()
                    if method_block:
                        blocks.append(method_block)
            continue

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = node.end_lineno or node.lineno
            block = "\n".join(lines[node.lineno - 1 : end_line]).strip()
            if block:
                blocks.append(block)

    return blocks


def _find_pattern_starts(content: str, patterns: tuple[re.Pattern[str], ...]) -> list[int]:
    """Return 1-based start lines for regex pattern matches."""
    starts: list[int] = []
    for pattern in patterns:
        for match in pattern.finditer(content):
            starts.append(content.count("\n", 0, match.start()) + 1)
    return starts


def _chunk_javascript_like(content: str) -> list[str]:
    """Extract JavaScript and TypeScript structural blocks."""
    starts = _find_pattern_starts(content, (JS_CLASS_PATTERN, *JS_FUNCTION_PATTERNS))
    return _extract_line_blocks(content, starts)


def _chunk_structurally(content: str, language: str) -> list[str]:
    """Extract structural code blocks based on language."""
    if language == "python":
        return _chunk_python(content)

    if language in {"javascript", "jsx", "typescript", "tsx"}:
        return _chunk_javascript_like(content)

    return []


def _fallback_chunks(content: str) -> list[str]:
    """Fallback to fixed-size overlapping text chunks."""
    return [chunk["text"] for chunk in chunk_text(content, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP)]


def _dedupe_blocks(blocks: list[str]) -> list[str]:
    """Remove duplicate blocks while preserving order."""
    seen: set[str] = set()
    unique_blocks: list[str] = []

    for block in blocks:
        if block in seen:
            continue
        seen.add(block)
        unique_blocks.append(block)

    return unique_blocks


def chunk_code(
    content: str,
    filename: str,
    language: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[CodeChunk]:
    """Split source code into semantic chunks with a size-based fallback."""
    normalized = content.strip()
    if not normalized:
        return []

    structural_blocks = _dedupe_blocks(_chunk_structurally(normalized, language))
    chunks: list[str] = []

    for block in structural_blocks:
        if len(block) <= chunk_size:
            chunks.append(block)
            continue
        chunks.extend(
            chunk["text"]
            for chunk in chunk_text(block, chunk_size, overlap)
        )

    if not chunks:
        chunks = _fallback_chunks(normalized)

    return [
        {
            "chunk_id": f"chunk_{index:04d}",
            "text": chunk,
            "filename": filename,
            "language": language,
        }
        for index, chunk in enumerate(chunks)
        if chunk.strip()
    ]
