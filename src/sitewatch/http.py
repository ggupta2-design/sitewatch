"""Bounded dependency-free HTTP transport for SiteWatch."""

from __future__ import annotations

import hashlib
import socket
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)

from .models import Observation, Target
from .safety import (
    SiteWatchError,
    validate_http_url,
    validate_public_resolution,
)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _SafeRedirect(HTTPRedirectHandler):
    def __init__(self, resolver):
        super().__init__()
        self.resolver = resolver

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url = validate_http_url(newurl)
        validate_public_resolution(safe_url, resolver=self.resolver)
        return super().redirect_request(req, fp, code, msg, headers, safe_url)


def _timestamp(now) -> datetime:
    value = now()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _observation_from_response(
    response,
    *,
    target: Target,
    checked_at: datetime,
    duration_ms: int,
) -> Observation:
    body = response.read(target.max_bytes + 1)
    if len(body) > target.max_bytes:
        return Observation(
            status=getattr(response, "status", response.getcode()),
            final_url=validate_http_url(response.geturl()),
            duration_ms=duration_ms,
            content_type=response.headers.get_content_type(),
            bytes_read=target.max_bytes,
            sha256=None,
            checked_at=checked_at,
            error_code="response_too_large",
        )
    return Observation(
        status=getattr(response, "status", response.getcode()),
        final_url=validate_http_url(response.geturl()),
        duration_ms=duration_ms,
        content_type=response.headers.get_content_type(),
        bytes_read=len(body),
        sha256=hashlib.sha256(body).hexdigest(),
        checked_at=checked_at,
    )


def observe_target(
    target: Target,
    *,
    resolver=socket.getaddrinfo,
    opener=None,
    clock=time.perf_counter,
    now=lambda: datetime.now(timezone.utc),
) -> Observation:
    """Fetch bounded response metadata without retaining the response body."""

    started = clock()
    checked_at = _timestamp(now)
    try:
        validate_public_resolution(target.url, resolver=resolver)
        selected = opener
        if selected is None:
            handler = (
                _SafeRedirect(resolver)
                if target.allow_redirects
                else _NoRedirect()
            )
            selected = build_opener(handler).open
        request = Request(
            target.url,
            headers={
                "Accept": "*/*",
                "User-Agent": "SiteWatch/0.1 (+local-health-check)",
            },
            method="GET",
        )
        try:
            response = selected(request, timeout=target.timeout_seconds)
        except HTTPError as exc:
            response = exc
        with response:
            duration_ms = max(0, round((clock() - started) * 1000))
            return _observation_from_response(
                response,
                target=target,
                checked_at=checked_at,
                duration_ms=duration_ms,
            )
    except SiteWatchError:
        error_code = "unsafe_destination"
    except (TimeoutError, socket.timeout):
        error_code = "timeout"
    except (URLError, OSError):
        error_code = "network_error"
    return Observation(
        status=None,
        final_url=None,
        duration_ms=max(0, round((clock() - started) * 1000)),
        content_type=None,
        bytes_read=0,
        sha256=None,
        checked_at=checked_at,
        error_code=error_code,
    )
