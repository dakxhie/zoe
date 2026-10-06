"""Web search and page reading pipeline for Zoe AI."""

from __future__ import annotations

import logging
import re

from web.cache import cache_page, get_cached_page, get_cached_retrieved_at
from web.reader import bound_page_result, fetch_page_text
from web.search import search_web

logger = logging.getLogger(__name__)

SNIPPET_DEDUP_CHARS = 200


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


def _normalize_snippet(text: str) -> str:
    """Normalize page text for duplicate snippet detection."""
    collapsed = re.sub(r"\s+", " ", text.strip().lower())
    return collapsed[:SNIPPET_DEDUP_CHARS]


def _truncation_marker(envelope: dict) -> str:
    """Visible truncation boundary for the model (A.1 §23.4)."""
    if not envelope.get("truncated"):
        return ""
    info = envelope.get("truncation") or {}
    returned = info.get("returned_chars")
    original = info.get("original_chars")
    if returned is not None and original is not None:
        return f"\n[truncated: showing the first {returned} of {original} characters of this page]"
    return "\n[truncated: page content shortened to fit Zoe's result limits]"


# Storage cap for the on-disk page cache (the pre-B2 reader output cap).
# This is not a context limit: every page, cached or downloaded, is bounded by
# ``bound_page_result`` before it can enter model context.
MAX_CACHE_CHARS = 20_000


def _fetch_page_text(url: str) -> tuple[str, str, bool] | None:
    """Return ``(unbounded_text, retrieved_at, cache_hit)`` for a turn-result URL.

    The text is not context-safe; ``retrieve_web_context_with_stats`` bounds it.
    """
    from web.policy import url_in_turn_results

    if not url_in_turn_results(url):
        # Neither cached nor downloaded content is used for URLs that did not
        # come from this turn's successful authorized search.
        return None

    cached_text = get_cached_page(url)
    if cached_text is not None:
        retrieved_at = get_cached_retrieved_at(url) or ""
        logger.info("Cache hit: %s", url)
        return cached_text, retrieved_at, True

    try:
        text, _error = fetch_page_text(url)
    except Exception as exc:
        logger.warning("Webpage read failed: %s", type(exc).__name__)
        return None

    if not text:
        return None

    cache_page(url, text[:MAX_CACHE_CHARS])
    retrieved_at = get_cached_retrieved_at(url) or ""
    logger.info("Downloaded: %s", url)
    return text, retrieved_at, False


def retrieve_web_context(query: str, max_pages: int = 3) -> str:
    """Search the web, read top pages, and return combined readable context."""
    result, _stats = retrieve_web_context_with_stats(query, max_pages=max_pages)
    return result


def _set_status(stats: dict) -> None:
    """Record the canonical structured web state (status + error.type)."""
    from web.policy import current_web_state

    state = current_web_state()
    stats["status"] = state.status.value if state.status is not None else "not_run"
    stats["error_type"] = state.error_type.value if state.error_type is not None else None


def retrieve_web_context_with_stats(
    query: str,
    max_pages: int = 3,
) -> tuple[str, dict[str, int | str]]:
    """Search the web and return context plus retrieval statistics.

    Phase B2: ``search_web`` is gated by ``web.policy``; ``query`` is never sent
    to the provider. Every page is bounded by the universal result layer
    (``tools.result_envelope``) before it can enter context. ``stats["status"]``
    and ``stats["error_type"]`` carry the canonical structured web state.
    """
    stats: dict[str, int | str] = {"pages_retrieved": 0, "cache_hits": 0, "downloads": 0}

    normalized_query = query.strip()
    if not normalized_query or max_pages <= 0:
        _set_status(stats)
        return "", stats

    try:
        results = search_web(normalized_query, max_results=max_pages)
    except Exception as exc:
        logger.warning("Web search failed during retrieval: %s", type(exc).__name__)
        _set_status(stats)
        return "", stats

    if not results:
        _set_status(stats)
        return "", stats

    pages: list[tuple[str, str, dict]] = []
    seen_urls: set[str] = set()
    seen_snippets: set[str] = set()

    for result in results:
        if len(pages) >= max_pages:
            break

        url = result.get("url", "")
        title = result.get("title", "").strip() or url

        if not url or url in seen_urls:
            continue

        fetched = _fetch_page_text(url)
        if fetched is None:
            continue

        raw_text, retrieved_at, cache_hit = fetched
        # Single authoritative bounding point for page content (A.1 §23/§24).
        envelope = bound_page_result(url, title, raw_text, retrieved_at)
        del raw_text
        if envelope["status"] != "success":
            # e.g. result_unrepresentable: nothing from this page enters context.
            stats["unrepresentable"] = int(stats.get("unrepresentable", 0)) + 1
            continue
        snippet_key = _normalize_snippet(envelope["result"]["content"])
        if snippet_key in seen_snippets:
            continue

        seen_urls.add(url)
        seen_snippets.add(snippet_key)

        if cache_hit:
            stats["cache_hits"] = int(stats["cache_hits"]) + 1
        else:
            stats["downloads"] = int(stats["downloads"]) + 1
        if envelope["truncated"]:
            stats["truncated_pages"] = int(stats.get("truncated_pages", 0)) + 1

        pages.append((title, url, envelope))

    from web.policy import record_pages_used

    record_pages_used([url for _title, url, _envelope in pages])

    _set_status(stats)
    if not pages:
        return "", stats

    stats["pages_retrieved"] = len(pages)

    blocks: list[str] = []
    for title, url, envelope in pages:
        page = envelope["result"]
        content = page["content"].rstrip()
        if not content:
            continue
        blocks.append(
            _format_page(page["title"] or title, url, content + _truncation_marker(envelope), page["retrieved_at"])
        )

    return "\n\n".join(blocks), stats
