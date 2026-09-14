import socket

import pytest

from sitewatch.safety import (
    SiteWatchError,
    validate_http_url,
    validate_public_resolution,
)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "ftp://example.com/file",
        "https://user:secret@example.com/",
        "https://example.com/page#private",
        "http://localhost/",
        "http://service.local/",
        "http://127.0.0.1/",
        "http://10.0.0.8/",
        "http://[::1]/",
        "https://example.com:99999/",
    ],
)
def test_rejects_unsafe_target_urls(value):
    with pytest.raises(SiteWatchError):
        validate_http_url(value)


def test_normalizes_public_http_url():
    assert (
        validate_http_url(" HTTPS://Example.COM/health?full=1 ")
        == "https://example.com/health?full=1"
    )


def test_accepts_public_ip_literal():
    assert validate_http_url("https://8.8.8.8/status") == (
        "https://8.8.8.8/status"
    )


def public_resolver(host, port, *, type):
    assert host == "example.com"
    assert port == 443
    assert type == socket.SOCK_STREAM
    return [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
    ]


def test_validates_public_dns_resolution():
    assert validate_public_resolution(
        "https://example.com/health",
        resolver=public_resolver,
    ) == ("93.184.216.34",)


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "::1", "169.254.1.1"])
def test_rejects_non_public_dns_answers(address):
    def resolver(host, port, *, type):
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (address, port))]

    with pytest.raises(SiteWatchError, match="non-public"):
        validate_public_resolution("https://example.com/", resolver=resolver)


def test_rejects_mixed_public_and_private_dns_answers():
    def resolver(host, port, *, type):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
        ]

    with pytest.raises(SiteWatchError, match="non-public"):
        validate_public_resolution("https://example.com/", resolver=resolver)
