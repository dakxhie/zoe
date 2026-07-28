"""Pytest coverage for web retrieval."""

from __future__ import annotations

from unittest.mock import patch

from web.retriever import _normalize_snippet, retrieve_web_context_with_stats


def test_normalize_snippet_collapses_whitespace() -> None:
    """Normalize snippets for duplicate detection."""
    assert _normalize_snippet("Hello   World") == "hello world"


def test_retrieve_web_context_deduplicates_urls_and_limits_pages() -> None:
    """Deduplicate URLs and cap page count."""
    duplicate_url = "https://example.com/a"
    search_results = [
        {"title": "A", "url": duplicate_url, "body": "First"},
        {"title": "A duplicate", "url": duplicate_url, "body": "Second"},
        {"title": "B", "url": "https://example.com/b", "body": "Third"},
        {"title": "C", "url": "https://example.com/c", "body": "Fourth"},
    ]

    with patch("web.retriever.search_web", return_value=search_results), patch(
        "web.retriever._fetch_page_text",
        side_effect=[
            ("Page one content " * 20, "2026-01-01", False),
            ("Page two content " * 20, "2026-01-01", False),
            ("Page three content " * 20, "2026-01-01", False),
        ],
    ):
        context, stats = retrieve_web_context_with_stats("example query", max_pages=3)

    assert stats["pages_retrieved"] == 3
    assert context.count("https://example.com/a") == 1
    assert "Sources:" not in context


def test_retrieve_web_context_skips_duplicate_snippets() -> None:
    """Skip repeated snippets from different URLs."""
    with patch(
        "web.retriever.search_web",
        return_value=[
            {"title": "A", "url": "https://example.com/a", "body": "Same"},
            {"title": "B", "url": "https://example.com/b", "body": "Same"},
        ],
    ), patch(
        "web.retriever._fetch_page_text",
        return_value=("Duplicate snippet content", "2026-01-01", False),
    ):
        _context, stats = retrieve_web_context_with_stats("duplicate query", max_pages=3)

    assert stats["pages_retrieved"] == 1
