"""Web search for Zoe AI."""

from web.cache import cache_page, clear_web_cache, get_cached_page
from web.reader import read_webpage
from web.retriever import retrieve_web_context, retrieve_web_context_with_stats
from web.search import WebSearchResult, search_web

__all__ = [
    "WebSearchResult",
    "cache_page",
    "clear_web_cache",
    "get_cached_page",
    "read_webpage",
    "retrieve_web_context",
    "retrieve_web_context_with_stats",
    "search_web",
]
