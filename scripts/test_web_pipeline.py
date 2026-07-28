"""Smoke test for source-aware web answer pipeline."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.context import (
    WEB_HEADING,
    WEB_SOURCE_INSTRUCTION,
    _build_chat_messages,
    _build_web_system_content,
    build_web_sources_footer,
)
from web.cache import clear_web_cache
from web.retriever import retrieve_web_context_with_stats

SAMPLE_WEB_CONTEXT = (
    "Source:\nPython.org\n\n"
    "URL:\nhttps://www.python.org\n\n"
    "Retrieved:\n2026-07-28 10:00 UTC\n\n"
    "Content:\nPython is a programming language."
)
SAMPLE_SOURCES = [("Python.org", "https://www.python.org")]


def _test_successful_retrieval() -> None:
    """Verify successful web retrieval returns context and stats."""
    with patch(
        "web.retriever.search_web",
        return_value=[
            {
                "title": "Python.org",
                "url": "https://www.python.org",
                "body": "Official site",
            }
        ],
    ), patch(
        "web.retriever.read_webpage",
        return_value="Python is a programming language.",
    ), patch("web.retriever.get_cached_page", return_value=None):
        context, stats = retrieve_web_context_with_stats("latest Python news", max_pages=1)

    if not context:
        raise SystemExit("Expected successful web retrieval context")

    if stats["pages_retrieved"] != 1:
        raise SystemExit(f"Expected 1 retrieved page, got {stats['pages_retrieved']}")

    print("ok: successful retrieval")


def _test_empty_retrieval() -> None:
    """Verify empty web retrieval falls back to normal chat generation."""
    with patch("web.retriever.search_web", return_value=[]):
        context, stats = retrieve_web_context_with_stats("latest Python news", max_pages=1)

    if context:
        raise SystemExit("Expected empty web retrieval context")

    messages = _build_chat_messages("latest Python news", [])
    system_message = messages[0]["content"]

    if WEB_HEADING in system_message:
        raise SystemExit("Empty web retrieval should not inject Web Context")

    if WEB_SOURCE_INSTRUCTION in system_message:
        raise SystemExit("Empty web retrieval should not inject web instructions")

    if stats["pages_retrieved"] != 0:
        raise SystemExit("Expected zero retrieved pages for empty search")

    print("ok: empty retrieval fallback")


def _test_cache_usage() -> None:
    """Verify cached pages are reused on repeated retrieval."""
    clear_web_cache()

    with patch(
        "web.retriever.search_web",
        return_value=[
            {
                "title": "Python.org",
                "url": "https://www.python.org",
                "body": "Official site",
            }
        ],
    ), patch(
        "web.retriever.read_webpage",
        return_value="Python is a programming language.",
    ), patch("web.retriever.get_cached_page", return_value=None):
        first_context, first_stats = retrieve_web_context_with_stats(
            "latest Python news",
            max_pages=1,
        )

    with patch(
        "web.retriever.search_web",
        return_value=[
            {
                "title": "Python.org",
                "url": "https://www.python.org",
                "body": "Official site",
            }
        ],
    ), patch(
        "web.retriever.read_webpage",
        side_effect=AssertionError("Cached page should be used"),
    ):
        second_context, second_stats = retrieve_web_context_with_stats(
            "latest Python news",
            max_pages=1,
        )

    if not first_context or not second_context:
        raise SystemExit("Expected cached retrieval to return context")

    if first_stats["downloads"] != 1:
        raise SystemExit("Expected one download on first retrieval")

    if second_stats["cache_hits"] != 1:
        raise SystemExit("Expected one cache hit on second retrieval")

    print("ok: cache usage")


def _test_source_footer_generation() -> None:
    """Verify source footer and web system prompt generation."""
    footer = build_web_sources_footer(SAMPLE_SOURCES)
    if "Sources:" not in footer:
        raise SystemExit("Expected Sources footer heading")

    if "Python.org — https://www.python.org" not in footer:
        raise SystemExit("Expected source line in footer")

    prepared_context = f"{SAMPLE_WEB_CONTEXT}\n\n{footer}"
    system_message = _build_web_system_content(prepared_context)

    if WEB_SOURCE_INSTRUCTION not in system_message:
        raise SystemExit("Expected web source instruction in system prompt")

    if "Sources:" not in system_message:
        raise SystemExit("Expected source footer in system prompt")

    print("ok: source footer generation")


def main() -> None:
    """Run web pipeline verification checks."""
    _test_successful_retrieval()
    _test_empty_retrieval()
    _test_cache_usage()
    _test_source_footer_generation()
    print("\nWeb pipeline tests passed.")


if __name__ == "__main__":
    main()
