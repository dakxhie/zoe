"""Web search and page reading pipeline for Zoe AI."""

from __future__ import annotations

import logging

from web.cache import cache_page, get_cached_page, get_cached_retrieved_at
from web.reader import read_webpage
from web.search import search_web

logger = logging.getLogger(__name__)

MAX_WEB_CONTEXT_CHARS = 12_000


def _format_page(title: str, url: str, content: str, retrieved_at: str) -> str:
    """Format one webpage into a readable context block."""
    return (
        f"Source:\n{title}\n\n"
        f"URL:\n{url}\n\n"
        f"Retrieved:\n{retrieved_at}\n\n"
        f"Content:\n{content}"
    )


def _header_length(title: str, url: str, retrieved_at: str) -> int:
    """Return the formatted block size without page content."""
    return len(_format_page(title, url, "", retrieved_at))


def _fetch_page_text(url: str) -> tuple[str, str, bool] | None:
    """Return cleaned page text, retrieval timestamp, and cache-hit flag."""
    cached_text = get_cached_page(url)
    if cached_text is not None:
        retrieved_at = get_cached_retrieved_at(url) or ""
        logger.info("Cache hit: %s", url)
        return cached_text, retrieved_at, True

    try:
        page_text = read_webpage(url)
    except Exception as exc:
        logger.warning("Webpage read failed for %s: %s", url, exc)
        return None

    if not page_text:
        return None

    cache_page(url, page_text)
    retrieved_at = get_cached_retrieved_at(url) or ""
    logger.info("Downloaded: %s", url)
    return page_text, retrieved_at, False


def retrieve_web_context(query: str, max_pages: int = 3) -> str:
    """Search the web, read top pages, and return combined readable context."""
    result, _stats = retrieve_web_context_with_stats(query, max_pages=max_pages)
    return result


def retrieve_web_context_with_stats(
    query: str,
    max_pages: int = 3,
) -> tuple[str, dict[str, int]]:
    """Search the web and return context plus retrieval statistics."""
    stats = {"pages_retrieved": 0, "cache_hits": 0, "downloads": 0}

    normalized_query = query.strip()
    if not normalized_query or max_pages <= 0:
        return "", stats

    try:
        results = search_web(normalized_query, max_results=max_pages)
    except Exception as exc:
        logger.warning("Web search failed during retrieval: %s", exc)
        return "", stats

    if not results:
        return "", stats

    pages: list[tuple[str, str, str, str]] = []
    seen_text: set[str] = set()

    for result in results:
        url = result.get("url", "").strip()
        title = result.get("title", "").strip() or url

        if not url:
            continue

        fetched = _fetch_page_text(url)
        if fetched is None:
            continue

        page_text, retrieved_at, cache_hit = fetched
        if cache_hit:
            stats["cache_hits"] += 1
        else:
            stats["downloads"] += 1

        if page_text in seen_text:
            continue

        seen_text.add(page_text)
        pages.append((title, url, page_text, retrieved_at))

    if not pages:
        return "", stats

    stats["pages_retrieved"] = len(pages)

    per_page_budget = MAX_WEB_CONTEXT_CHARS // len(pages)
    blocks: list[str] = []

    for title, url, page_text, retrieved_at in pages:
        header_length = _header_length(title, url, retrieved_at)
        content_budget = max(0, per_page_budget - header_length)
        truncated_content = page_text[:content_budget].rstrip()

        if not truncated_content:
            continue

        blocks.append(_format_page(title, url, truncated_content, retrieved_at))

    return "\n\n".join(blocks)[:MAX_WEB_CONTEXT_CHARS].rstrip(), stats
