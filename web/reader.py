"""Webpage download and text extraction for Zoe AI."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 10
MAX_OUTPUT_CHARS = 20_000
USER_AGENT = "ZoeAI/1.0 (+https://github.com/dakxhie/zoe)"

REMOVED_TAGS = (
    "script",
    "style",
    "noscript",
    "header",
    "footer",
    "nav",
    "aside",
    "svg",
)

SUPPORTED_CONTENT_TYPES = (
    "text/html",
    "application/xhtml+xml",
)


def _is_valid_url(url: str) -> bool:
    """Return True when the URL has an http or https scheme and a host."""
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_supported_content_type(content_type: str) -> bool:
    """Return True when the response looks like HTML."""
    normalized = content_type.split(";", 1)[0].strip().lower()
    return any(normalized.startswith(supported) for supported in SUPPORTED_CONTENT_TYPES)


def _download_page(url: str) -> requests.Response | None:
    """Download a webpage, retrying without SSL verification only when needed."""
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=True,
            headers=headers,
        )
        response.raise_for_status()
        return response
    except requests.exceptions.SSLError:
        logger.warning("SSL verification failed for %s; retrying without verification", url)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
        logger.warning("Webpage download failed for %s: %s", url, exc)
        return None
    except requests.exceptions.RequestException as exc:
        logger.warning("Webpage download failed for %s: %s", url, exc)
        return None

    try:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=True,
            headers=headers,
            verify=False,
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as exc:
        logger.warning("Webpage download failed for %s: %s", url, exc)
        return None


def _remove_unwanted_tags(soup: BeautifulSoup) -> None:
    """Remove non-content tags from the parsed document."""
    for tag_name in REMOVED_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()


def _extract_visible_text(html: str) -> str:
    """Parse HTML and return cleaned visible text."""
    soup = BeautifulSoup(html, "html.parser")
    _remove_unwanted_tags(soup)

    text = soup.get_text(separator="\n", strip=True)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def read_webpage(url: str) -> str:
    """Download a webpage and return cleaned readable text."""
    normalized_url = url.strip()
    if not normalized_url or not _is_valid_url(normalized_url):
        logger.warning("Invalid webpage URL: %s", url)
        return ""

    response = _download_page(normalized_url)
    if response is None:
        return ""

    content_type = response.headers.get("Content-Type", "")
    if content_type and not _is_supported_content_type(content_type):
        logger.warning("Unsupported content type for %s: %s", normalized_url, content_type)
        return ""

    encoding = response.encoding or response.apparent_encoding or "utf-8"
    try:
        html = response.content.decode(encoding, errors="replace")
    except (LookupError, UnicodeError) as exc:
        logger.warning("Could not decode webpage %s: %s", normalized_url, exc)
        return ""

    if not html.strip():
        return ""

    text = _extract_visible_text(html)
    if not text:
        return ""

    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS].rstrip()

    return text
