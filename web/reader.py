"""Webpage download and text extraction for Zoe AI."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from tools.result_envelope import ErrorType, ResultStatus, bound_result, error_envelope

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 10
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


MAX_REDIRECTS = 3


@dataclass(frozen=True)
class _Download:
    response: requests.Response | None
    status: ResultStatus = ResultStatus.SUCCESS
    error_type: ErrorType | None = None
    detail: str = ""


def _download_page(url: str) -> _Download:
    """Download a webpage with normal TLS certificate verification.

    Phase B2: there is no retry with verification disabled. A TLS failure is a
    typed ``fetch_failed`` error. Redirects are followed manually (at most
    ``MAX_REDIRECTS``) so every hop passes the same URL target checks; only a
    fixed User-Agent is sent (no cookies, no auth headers).
    """
    from web.policy import check_fetch_target

    headers = {"User-Agent": USER_AGENT}
    current = url
    for _hop in range(MAX_REDIRECTS + 1):
        try:
            response = requests.get(
                current,
                timeout=REQUEST_TIMEOUT_SECONDS,
                allow_redirects=False,
                headers=headers,
            )
        except requests.exceptions.SSLError:
            logger.warning("TLS certificate verification failed; page not fetched")
            return _Download(None, ResultStatus.ERROR, ErrorType.FETCH_FAILED, "tls_verification_failed")
        except requests.exceptions.Timeout:
            logger.warning("Webpage download timed out")
            return _Download(None, ResultStatus.TIMEOUT, ErrorType.TIMEOUT, "timeout")
        except requests.exceptions.ConnectionError:
            logger.warning("Webpage download failed: connection error")
            return _Download(None, ResultStatus.ERROR, ErrorType.NETWORK_UNAVAILABLE, "connection_error")
        except requests.exceptions.RequestException as exc:
            logger.warning("Webpage download failed: %s", type(exc).__name__)
            return _Download(None, ResultStatus.ERROR, ErrorType.FETCH_FAILED, "request_error")

        if getattr(response, "is_redirect", False):
            location = response.headers.get("Location", "")
            target = urljoin(current, location) if location else ""
            check = check_fetch_target(target) if target else None
            if check is None or not check.allowed:
                logger.warning("Redirect refused by web policy")
                return _Download(
                    None,
                    ResultStatus.DENIED,
                    (check.error_type if check else None) or ErrorType.WEB_NOT_AUTHORIZED,
                    "redirect_refused",
                )
            current = target
            continue

        try:
            response.raise_for_status()
        except requests.exceptions.RequestException:
            logger.warning("Webpage download failed: HTTP error")
            return _Download(None, ResultStatus.ERROR, ErrorType.FETCH_FAILED, "http_error")
        return _Download(response)

    return _Download(None, ResultStatus.ERROR, ErrorType.FETCH_FAILED, "too_many_redirects")


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


def bound_page_result(url: str, title: str, text: str, retrieved_at: str = "") -> dict:
    """Bound extracted page text through the universal result layer (A.1 §24).

    Every page that may enter model context, downloaded or cached, passes
    through here: the ``fetch_page`` per-tool limit (8 KB of extracted text)
    and the global 16 KB / 1,000-token ceilings apply, with deterministic
    truncation metadata.
    """
    return bound_result(
        "fetch_page",
        {"url": url, "title": title, "retrieved_at": retrieved_at, "content": text},
        trust="untrusted_external",
        source={"kind": "web", "url": url},
    )


def _fetch_error(url: str, status: ResultStatus, error_type: ErrorType, detail: str) -> dict:
    return error_envelope(
        "fetch_page",
        status,
        error_type,
        trust="untrusted_external",
        source={"kind": "web", "url": url},
        metadata={"detail": detail},
    )


def fetch_page_text(url: str) -> tuple[str | None, dict | None]:
    """Gated download + extraction: ``(text, None)`` or ``(None, error_envelope)``.

    The returned text is NOT yet bounded and must never be placed in model
    context directly; callers pass it through ``bound_page_result`` (as
    ``fetch_page`` and ``web.retriever`` do).
    """
    normalized_url = url.strip()
    if not normalized_url or not _is_valid_url(normalized_url):
        return None, _fetch_error(url, ResultStatus.DENIED, ErrorType.WEB_NOT_AUTHORIZED, "invalid_url")

    from web.policy import authorize_fetch

    decision = authorize_fetch(normalized_url)
    if not decision.allowed:
        logger.info("Webpage fetch refused by web policy (%s)", decision.reason)
        return None, _fetch_error(
            normalized_url,
            decision.status or ResultStatus.DENIED,
            decision.error_type or ErrorType.WEB_NOT_AUTHORIZED,
            decision.reason,
        )

    download = _download_page(normalized_url)
    if download.response is None:
        return None, _fetch_error(
            normalized_url, download.status, download.error_type or ErrorType.FETCH_FAILED, download.detail
        )
    response = download.response

    content_type = response.headers.get("Content-Type", "")
    if content_type and not _is_supported_content_type(content_type):
        logger.warning("Unsupported content type for fetched page: %s", content_type)
        return None, _fetch_error(
            normalized_url, ResultStatus.ERROR, ErrorType.FETCH_FAILED, "unsupported_content_type"
        )

    encoding = response.encoding or response.apparent_encoding or "utf-8"
    try:
        html = response.content.decode(encoding, errors="replace")
    except (LookupError, UnicodeError):
        return None, _fetch_error(normalized_url, ResultStatus.ERROR, ErrorType.FETCH_FAILED, "decode_error")

    text = _extract_visible_text(html) if html.strip() else ""
    if not text:
        return None, _fetch_error(normalized_url, ResultStatus.ERROR, ErrorType.FETCH_FAILED, "empty_page")
    return text, None


def fetch_page(url: str, title: str = "", retrieved_at: str = "") -> dict:
    """Gated page fetch returning a bounded ``fetch_page`` tool_result envelope."""
    text, error = fetch_page_text(url)
    if text is None:
        return error  # type: ignore[return-value]
    return bound_page_result(url.strip(), title, text, retrieved_at)


def read_webpage(url: str) -> str:
    """Compatibility wrapper: bounded page text, or "" when the fetch failed or was refused."""
    envelope = fetch_page(url)
    if envelope["status"] != ResultStatus.SUCCESS.value:
        return ""
    return envelope["result"]["content"]
