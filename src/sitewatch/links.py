"""Bounded, deterministic link discovery and audit models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import urldefrag, urljoin, urlsplit

from .safety import SiteWatchError, validate_http_url


@dataclass(frozen=True)
class LinkAuditPolicy:
    """Explicit limits for one page-level link audit."""

    source_url: str
    max_links: int = 50
    max_page_bytes: int = 1_000_000
    timeout_seconds: float = 10.0
    include_external: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_url", validate_http_url(self.source_url))
        if (
            isinstance(self.max_links, bool)
            or not isinstance(self.max_links, int)
            or not 1 <= self.max_links <= 500
        ):
            raise SiteWatchError("max_links must be from 1 to 500")
        if (
            isinstance(self.max_page_bytes, bool)
            or not isinstance(self.max_page_bytes, int)
            or not 1 <= self.max_page_bytes <= 10_000_000
        ):
            raise SiteWatchError("max_page_bytes must be from 1 to 10000000")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not 0.1 <= self.timeout_seconds <= 60
        ):
            raise SiteWatchError("timeout_seconds must be from 0.1 to 60")
        object.__setattr__(self, "timeout_seconds", float(self.timeout_seconds))
        if not isinstance(self.include_external, bool):
            raise SiteWatchError("include_external must be true or false")


@dataclass(frozen=True)
class HtmlPage:
    """Ephemeral bounded HTML input returned by the transport layer."""

    final_url: str
    content_type: str
    body: bytes


@dataclass(frozen=True)
class LinkDiscovery:
    """Value-free discovery metadata and normalized unique destinations."""

    urls: tuple[str, ...]
    discovered: int
    skipped_external: int
    skipped_unsupported: int
    truncated: bool


class LinkState(str, Enum):
    HEALTHY = "healthy"
    BROKEN = "broken"
    ERROR = "error"


@dataclass(frozen=True)
class LinkResult:
    """One destination result without response content."""

    url: str
    state: LinkState
    status: int | None
    final_url: str | None
    duration_ms: int
    error_code: str | None = None

    @property
    def healthy(self) -> bool:
        return self.state is LinkState.HEALTHY


@dataclass(frozen=True)
class LinkAudit:
    """Bounded link results for one source page."""

    source_url: str
    final_source_url: str | None
    results: tuple[LinkResult, ...]
    discovered: int
    skipped_external: int
    skipped_unsupported: int
    truncated: bool
    source_error: str | None = None

    @property
    def healthy(self) -> bool:
        return (
            self.source_error is None
            and bool(self.results)
            and all(item.healthy for item in self.results)
        )

    @property
    def healthy_count(self) -> int:
        return sum(item.healthy for item in self.results)

    @property
    def broken_count(self) -> int:
        return sum(item.state is LinkState.BROKEN for item in self.results)

    @property
    def error_count(self) -> int:
        return sum(item.state is LinkState.ERROR for item in self.results)


class _HrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag.casefold() not in {"a", "area"}:
            return
        for name, value in attrs:
            if name.casefold() == "href" and isinstance(value, str):
                self.hrefs.append(value)
                break


def _origin(url: str) -> tuple[str, str, int]:
    parts = urlsplit(url)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    return parts.scheme.casefold(), (parts.hostname or "").casefold(), port


def discover_links(
    body: bytes,
    *,
    base_url: str,
    policy: LinkAuditPolicy,
) -> LinkDiscovery:
    """Extract bounded unique HTTP(S) destinations without retaining HTML."""

    if not isinstance(body, bytes):
        raise SiteWatchError("page body must be bytes")
    if len(body) > policy.max_page_bytes:
        raise SiteWatchError("source page exceeded max_page_bytes")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SiteWatchError("source page is not valid UTF-8") from exc

    parser = _HrefParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:
        raise SiteWatchError("source page HTML could not be parsed") from exc

    base = validate_http_url(base_url)
    source_origin = _origin(base)
    urls: list[str] = []
    seen: set[str] = set()
    discovered = 0
    skipped_external = 0
    skipped_unsupported = 0
    truncated = False

    for href in parser.hrefs:
        value = href.strip()
        if not value or value.startswith("#"):
            continue
        joined, _ = urldefrag(urljoin(base, value))
        try:
            normalized = validate_http_url(joined)
        except SiteWatchError:
            skipped_unsupported += 1
            continue
        discovered += 1
        if not policy.include_external and _origin(normalized) != source_origin:
            skipped_external += 1
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        if len(urls) >= policy.max_links:
            truncated = True
            continue
        urls.append(normalized)

    return LinkDiscovery(
        urls=tuple(urls),
        discovered=discovered,
        skipped_external=skipped_external,
        skipped_unsupported=skipped_unsupported,
        truncated=truncated,
    )


def audit_links(
    policy: LinkAuditPolicy,
    *,
    fetch_page: Callable[[LinkAuditPolicy], HtmlPage],
    check_link: Callable[[str, LinkAuditPolicy], LinkResult],
) -> LinkAudit:
    """Fetch, discover, and check links sequentially within explicit bounds."""

    try:
        page = fetch_page(policy)
        if page.content_type.casefold() != "text/html":
            raise SiteWatchError("source page content type is not text/html")
        discovery = discover_links(
            page.body,
            base_url=page.final_url,
            policy=policy,
        )
    except SiteWatchError as exc:
        return LinkAudit(
            source_url=policy.source_url,
            final_source_url=None,
            results=(),
            discovered=0,
            skipped_external=0,
            skipped_unsupported=0,
            truncated=False,
            source_error=str(exc),
        )

    results = tuple(check_link(url, policy) for url in discovery.urls)
    return LinkAudit(
        source_url=policy.source_url,
        final_source_url=page.final_url,
        results=results,
        discovered=discovery.discovered,
        skipped_external=discovery.skipped_external,
        skipped_unsupported=discovery.skipped_unsupported,
        truncated=discovery.truncated,
    )
