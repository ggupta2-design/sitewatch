"""Target URL safeguards for SiteWatch."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit


class SiteWatchError(ValueError):
    """Raised when a check cannot be performed safely."""


def validate_http_url(value: str) -> str:
    """Return a normalized public HTTP(S) URL or reject unsafe target forms."""

    if not isinstance(value, str):
        raise SiteWatchError("target URL must be text")
    cleaned = value.strip()
    if not cleaned:
        raise SiteWatchError("target URL cannot be blank")
    if len(cleaned) > 2048:
        raise SiteWatchError("target URL cannot exceed 2048 characters")
    if any(character.isspace() or ord(character) < 32 for character in cleaned):
        raise SiteWatchError("target URL cannot contain whitespace or controls")

    parts = urlsplit(cleaned)
    if parts.scheme.casefold() not in {"http", "https"}:
        raise SiteWatchError("target URL must use http or https")
    if parts.username is not None or parts.password is not None:
        raise SiteWatchError("target URL cannot contain credentials")
    if parts.fragment:
        raise SiteWatchError("target URL cannot contain a fragment")
    hostname = parts.hostname
    if not hostname:
        raise SiteWatchError("target URL must include a hostname")
    try:
        parts.port
    except ValueError as exc:
        raise SiteWatchError("target URL contains an invalid port") from exc

    lowered = hostname.rstrip(".").casefold()
    if (
        lowered == "localhost"
        or lowered.endswith(".localhost")
        or lowered.endswith(".local")
    ):
        raise SiteWatchError("target URL cannot use a local hostname")
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise SiteWatchError("target URL cannot use a non-public IP address")

    host = lowered
    if ":" in host:
        host = f"[{host}]"
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    return urlunsplit(
        (
            parts.scheme.casefold(),
            host,
            parts.path or "/",
            parts.query,
            "",
        )
    )


def validate_public_resolution(url: str, *, resolver=socket.getaddrinfo) -> tuple[str, ...]:
    """Resolve a validated target and reject any non-public destination address."""

    parts = urlsplit(validate_http_url(url))
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        records = resolver(parts.hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise SiteWatchError("target hostname could not be resolved") from exc
    addresses = sorted({record[4][0] for record in records})
    if not addresses:
        raise SiteWatchError("target hostname did not resolve to an address")
    for value in addresses:
        try:
            address = ipaddress.ip_address(value)
        except ValueError as exc:
            raise SiteWatchError("target resolved to an invalid address") from exc
        if not address.is_global:
            raise SiteWatchError("target resolved to a non-public IP address")
    return tuple(addresses)
