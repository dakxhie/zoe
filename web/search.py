"""DuckDuckGo web search for Zoe AI.

Phase B2: ``provider_search`` is the only code that talks to the search
provider, and it is only called by ``web.policy.gated_search``. The public
``search_web`` helper is a gated compatibility wrapper: it never sends the
caller's text, only the query authorized for the current user turn.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from tools.result_envelope import ErrorType, ResultStatus
    from web.policy import SearchOutcome

logger = logging.getLogger(__name__)

# Matches the provider's own default and the existing page-reader timeout.
SEARCH_TIMEOUT_SECONDS = 10
# One provider backend per search (no fallback to a second backend = no retry).
SEARCH_BACKEND = "html"


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


def _classify_exception(exc: BaseException) -> "tuple[ResultStatus, ErrorType, str]":
    """Map a provider exception to a canonical (status, error.type, internal detail).

    Only the canonical error types are produced: a missing provider package or
    an unclassified provider error means the web could not be searched, so the
    public type is ``network_unavailable``; the internal detail keeps the
    distinction for logs.
    """
    from web.policy import DIAG_PROVIDER_ERROR, DIAG_PROVIDER_MISSING

    from tools.result_envelope import ErrorType, ResultStatus

    # The provider wraps transport errors (``DuckDuckGoSearchException(err)``,
    # ``raise ... from ex``), so look a few levels into the chain. Only exception
    # types are inspected; messages (which may echo the query or URL) are not.
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None and len(chain) < 4 and current not in chain:
        chain.append(current)
        inner = current.args[0] if current.args and isinstance(current.args[0], BaseException) else None
        current = inner or current.__cause__
    for item in chain:
        if isinstance(item, ImportError):
            return ResultStatus.ERROR, ErrorType.NETWORK_UNAVAILABLE, DIAG_PROVIDER_MISSING
    for item in chain:
        if isinstance(item, TimeoutError) or "timeout" in type(item).__name__.lower():
            return ResultStatus.TIMEOUT, ErrorType.TIMEOUT, "timeout"
    for item in chain:
        name = type(item).__name__.lower()
        if isinstance(item, (ConnectionError, OSError)) or "connect" in name or "network" in name:
            return ResultStatus.ERROR, ErrorType.NETWORK_UNAVAILABLE, "connection_error"
    return ResultStatus.ERROR, ErrorType.NETWORK_UNAVAILABLE, DIAG_PROVIDER_ERROR


def provider_search(query: str, max_results: int) -> "SearchOutcome":
    """Call the search provider once. Only ``web.policy.gated_search`` may call this."""
    from tools.result_envelope import ErrorType, ResultStatus
    from web.policy import DIAG_PROVIDER_MISSING, SearchOutcome, WebItem, _domain

    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.warning("duckduckgo_search is not installed")
        return SearchOutcome(
            ResultStatus.ERROR, ErrorType.NETWORK_UNAVAILABLE, query=query, detail=DIAG_PROVIDER_MISSING
        )

    try:
        # TLS verification stays on, and a single fixed backend is used: the
        # provider's ``backend="auto"`` silently retries a failed search on a
        # second backend, and Phase B2 allows no retries.
        with DDGS(timeout=SEARCH_TIMEOUT_SECONDS, verify=True) as ddgs:
            raw_results = ddgs.text(
                query,
                max_results=max_results,
                timelimit=None,
                backend=SEARCH_BACKEND,
            )
    except Exception as exc:
        status, error_type, detail = _classify_exception(exc)
        logger.warning("Web search failed (%s/%s): %s", error_type.value, detail, type(exc).__name__)
        return SearchOutcome(status, error_type, query=query, detail=detail)

    items: list[WebItem] = []
    for raw in raw_results or []:
        if not isinstance(raw, dict):
            continue
        normalized = _normalize_result(raw)
        if normalized is None:
            continue
        items.append(
            WebItem(
                rank=len(items) + 1,
                title=normalized["title"],
                url=normalized["url"],
                snippet=normalized["body"],
                source_domain=_domain(normalized["url"]),
            )
        )
        if len(items) >= max_results:
            break

    if not items:
        return SearchOutcome(ResultStatus.ERROR, ErrorType.NO_RESULTS, query=query)
    return SearchOutcome(ResultStatus.SUCCESS, None, query=query, items=tuple(items))


def search_web(query: str, max_results: int = 5) -> list[WebSearchResult]:
    """Gated web search: returns results only for the current turn's authorized query.

    ``query`` is accepted for compatibility but is never sent to the provider.
    Returns ``[]`` when web access is not authorized, blocked, or failed; the
    typed reason is available from ``web.policy.current_web_state()``.
    """
    if max_results <= 0:
        return []
    from web.policy import gated_search

    outcome = gated_search(query, max_results=max_results)
    return [
        {"title": item["title"], "url": item["url"], "body": item["body"]}
        for item in outcome.as_search_results()
    ]
