import socket
from email.message import Message
from urllib.error import URLError

import pytest

from sitewatch.link_http import check_link_destination, fetch_html_page
from sitewatch.links import LinkAuditPolicy, LinkState
from sitewatch.safety import SiteWatchError


def public_resolver(host, port, *, type):
    return [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
    ]


class Response:
    def __init__(
        self,
        body=b"<a href='/about'>About</a>",
        status=200,
        url="https://example.com/",
        content_type="text/html; charset=utf-8",
    ):
        self.body = body
        self.status = status
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.read_called = False

    def read(self, size):
        self.read_called = True
        return self.body[:size]

    def getcode(self):
        return self.status

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def policy(**changes):
    values = {"source_url": "https://example.com/"}
    values.update(changes)
    return LinkAuditPolicy(**values)


def test_fetches_bounded_html_for_immediate_parsing():
    response = Response()

    page = fetch_html_page(
        policy(max_page_bytes=100),
        resolver=public_resolver,
        opener=lambda request, timeout: response,
    )

    assert page.body == b"<a href='/about'>About</a>"
    assert page.content_type == "text/html"
    assert page.final_url == "https://example.com/"
    assert response.read_called is True


def test_rejects_oversized_source_page():
    with pytest.raises(SiteWatchError, match="exceeded max_page_bytes"):
        fetch_html_page(
            policy(max_page_bytes=4),
            resolver=public_resolver,
            opener=lambda request, timeout: Response(body=b"12345"),
        )


def test_rejects_non_html_source_page():
    with pytest.raises(SiteWatchError, match="content type"):
        fetch_html_page(
            policy(),
            resolver=public_resolver,
            opener=lambda request, timeout: Response(
                body=b"{}",
                content_type="application/json",
            ),
        )


def test_link_check_does_not_read_destination_body():
    response = Response(body=b"private page contents")

    result = check_link_destination(
        "https://example.com/about",
        policy(),
        resolver=public_resolver,
        opener=lambda request, timeout: response,
        clock=iter([1.0, 1.025]).__next__,
    )

    assert result.state is LinkState.HEALTHY
    assert result.status == 200
    assert result.duration_ms == 25
    assert response.read_called is False
    assert not hasattr(result, "body")


def test_http_error_status_is_broken_not_transport_error():
    result = check_link_destination(
        "https://example.com/missing",
        policy(),
        resolver=public_resolver,
        opener=lambda request, timeout: Response(status=404),
    )

    assert result.state is LinkState.BROKEN
    assert result.status == 404
    assert result.error_code is None


def test_private_resolution_blocks_link_request():
    opened = False

    def resolver(host, port, *, type):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
        ]

    def opener(request, timeout):
        nonlocal opened
        opened = True
        return Response()

    result = check_link_destination(
        "https://example.com/private",
        policy(),
        resolver=resolver,
        opener=opener,
    )

    assert result.state is LinkState.ERROR
    assert result.error_code == "unsafe_destination"
    assert opened is False


def test_network_failure_returns_stable_link_error():
    def opener(request, timeout):
        raise URLError("private transport detail")

    result = check_link_destination(
        "https://example.com/unavailable",
        policy(),
        resolver=public_resolver,
        opener=opener,
    )

    assert result.state is LinkState.ERROR
    assert result.error_code == "network_error"
    assert "private transport detail" not in repr(result)
