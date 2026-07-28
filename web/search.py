"""DuckDuckGo web search for Zoe AI."""

from __future__ import annotations

import logging
from typing import TypedDict

logger = logging.getLogger(__name__)


class WebSearchResult(TypedDict):
    """A single web search result."""

    title: str
    url: str
    body: str


def _normalize_result(raw: dict[str, object]) -> WebSearchResult | None:
    """Convert a DuckDuckGo result into the public search format."""
    title = str(raw.get("title", "")).strip()
    url = str(raw.get("href") or raw.get("url") or "").strip()
    body = str(raw.get("body", "")).strip()

    if not title and not url and not body:
        return None

    return {
        "title": title,
        "url": url,
        "body": body,
    }


def search_web(query: str, max_results: int = 5) -> list[WebSearchResult]:
    """Search the web with DuckDuckGo and return normalized results."""
    normalized_query = query.strip()
    if not normalized_query or max_results <= 0:
        return []

    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.warning("duckduckgo_search is not installed")
        return []

    try:
        with DDGS() as ddgs:
            raw_results = ddgs.text(
                normalized_query,
                max_results=max_results,
                timelimit=None,
            )
    except (OSError, TimeoutError, ConnectionError) as exc:
        logger.warning("Web search network error: %s", exc)
        return []
    except Exception as exc:
        logger.warning("Web search failed: %s", exc)
        return []

    if not raw_results:
        return []

    results: list[WebSearchResult] = []

    for raw in raw_results:
        if not isinstance(raw, dict):
            continue

        normalized = _normalize_result(raw)
        if normalized is not None:
            results.append(normalized)

        if len(results) >= max_results:
            break

    return results
