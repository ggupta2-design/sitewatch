"""Safe HTTP transport for bounded link audits."""

from __future__ import annotations

import socket
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from .http import _SafeRedirect
from .links import (
    HtmlPage,
    LinkAuditPolicy,
    LinkResult,
    LinkState,
)
from .safety import (
    SiteWatchError,
    validate_http_url,
    validate_public_resolution,
)


def _selected_opener(resolver, opener):
    if opener is not None:
        return opener
    return build_opener(_SafeRedirect(resolver)).open


def fetch_html_page(
    policy: LinkAuditPolicy,
    *,
    resolver=socket.getaddrinfo,
    opener=None,
) -> HtmlPage:
    """Fetch one bounded HTML page for immediate link extraction."""

    try:
        validate_public_resolution(policy.source_url, resolver=resolver)
        request = Request(
            policy.source_url,
            headers={
                "Accept": "text/html",
                "User-Agent": "SiteWatch/0.3 (+bounded-link-audit)",
            },
            method="GET",
        )
        selected = _selected_opener(resolver, opener)
        try:
            response = selected(request, timeout=policy.timeout_seconds)
        except HTTPError as exc:
            response = exc
        with response:
            status = getattr(response, "status", response.getcode())
            if not 200 <= status <= 399:
                raise SiteWatchError(f"source page returned HTTP {status}")
            final_url = validate_http_url(response.geturl())
            content_type = response.headers.get_content_type().casefold()
            if content_type != "text/html":
                raise SiteWatchError("source page content type is not text/html")
            body = response.read(policy.max_page_bytes + 1)
            if len(body) > policy.max_page_bytes:
                raise SiteWatchError("source page exceeded max_page_bytes")
            return HtmlPage(
                final_url=final_url,
                content_type=content_type,
                body=body,
            )
    except SiteWatchError:
        raise
    except (TimeoutError, socket.timeout) as exc:
        raise SiteWatchError("source page request timed out") from exc
    except (URLError, OSError) as exc:
        raise SiteWatchError("source page network request failed") from exc


def check_link_destination(
    url: str,
    policy: LinkAuditPolicy,
    *,
    resolver=socket.getaddrinfo,
    opener=None,
    clock=time.perf_counter,
) -> LinkResult:
    """Check one destination without reading or retaining its response body."""

    normalized = validate_http_url(url)
    started = clock()
    try:
        validate_public_resolution(normalized, resolver=resolver)
        request = Request(
            normalized,
            headers={
                "Accept": "*/*",
                "User-Agent": "SiteWatch/0.3 (+bounded-link-audit)",
            },
            method="GET",
        )
        selected = _selected_opener(resolver, opener)
        try:
            response = selected(request, timeout=policy.timeout_seconds)
        except HTTPError as exc:
            response = exc
        with response:
            status = getattr(response, "status", response.getcode())
            final_url = validate_http_url(response.geturl())
            return LinkResult(
                url=normalized,
                state=(
                    LinkState.HEALTHY
                    if 200 <= status <= 399
                    else LinkState.BROKEN
                ),
                status=status,
                final_url=final_url,
                duration_ms=max(0, round((clock() - started) * 1000)),
                error_code=None,
            )
    except SiteWatchError:
        error_code = "unsafe_destination"
    except (TimeoutError, socket.timeout):
        error_code = "timeout"
    except (URLError, OSError):
        error_code = "network_error"
    return LinkResult(
        url=normalized,
        state=LinkState.ERROR,
        status=None,
        final_url=None,
        duration_ms=max(0, round((clock() - started) * 1000)),
        error_code=error_code,
    )
