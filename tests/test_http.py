import hashlib
import socket
from datetime import datetime, timezone
from email.message import Message
from urllib.error import URLError

from sitewatch.http import observe_target
from sitewatch.models import Target


def public_resolver(host, port, *, type):
    return [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
    ]


class Response:
    def __init__(self, body=b"ok", status=200, url="https://example.com/"):
        self.body = body
        self.status = status
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = "text/plain; charset=utf-8"

    def read(self, size):
        return self.body[:size]

    def getcode(self):
        return self.status

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def target(**changes):
    values = {
        "name": "homepage",
        "url": "https://example.com/",
        "max_bytes": 10,
    }
    values.update(changes)
    return Target(**values)


def test_observes_bounded_response_metadata_without_body():
    response = Response(body=b"healthy")

    result = observe_target(
        target(),
        resolver=public_resolver,
        opener=lambda request, timeout: response,
        clock=iter([1.0, 1.125]).__next__,
        now=lambda: datetime(2026, 9, 14, tzinfo=timezone.utc),
    )

    assert result.status == 200
    assert result.duration_ms == 125
    assert result.content_type == "text/plain"
    assert result.bytes_read == 7
    assert result.sha256 == hashlib.sha256(b"healthy").hexdigest()
    assert result.error_code is None
    assert not hasattr(result, "body")


def test_stops_hashing_when_response_exceeds_limit():
    result = observe_target(
        target(max_bytes=4),
        resolver=public_resolver,
        opener=lambda request, timeout: Response(body=b"12345"),
        clock=iter([1.0, 1.1]).__next__,
    )

    assert result.error_code == "response_too_large"
    assert result.bytes_read == 4
    assert result.sha256 is None


def test_private_dns_answer_blocks_request():
    opened = False

    def resolver(host, port, *, type):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
        ]

    def opener(request, timeout):
        nonlocal opened
        opened = True
        return Response()

    result = observe_target(target(), resolver=resolver, opener=opener)

    assert result.error_code == "unsafe_destination"
    assert result.status is None
    assert opened is False


def test_network_failure_returns_stable_error_code():
    def opener(request, timeout):
        raise URLError("private transport detail")

    result = observe_target(
        target(),
        resolver=public_resolver,
        opener=opener,
    )

    assert result.error_code == "network_error"
    assert result.final_url is None
    assert result.bytes_read == 0
