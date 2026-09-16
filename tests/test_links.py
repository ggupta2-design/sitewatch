import pytest

from sitewatch.links import (
    HtmlPage,
    LinkAuditPolicy,
    LinkResult,
    LinkState,
    audit_links,
    discover_links,
)
from sitewatch.safety import SiteWatchError


def policy(**changes):
    source_url = changes.pop(
        "source_url", "https://example.com/docs/index.html"
    )
    return LinkAuditPolicy(source_url=source_url, **changes)


def healthy(url, selected):
    return LinkResult(
        url=url,
        state=LinkState.HEALTHY,
        status=200,
        final_url=url,
        duration_ms=5,
    )


def test_discovers_relative_links_deterministically_and_deduplicates():
    body = b"""
    <a href="/about">About</a>
    <a href="../help#install">Help</a>
    <a href="/about">About again</a>
    <area href="https://example.com/map">
    """

    found = discover_links(
        body,
        base_url="https://example.com/docs/index.html",
        policy=policy(),
    )

    assert found.urls == (
        "https://example.com/about",
        "https://example.com/help",
        "https://example.com/map",
    )
    assert found.discovered == 4
    assert found.skipped_external == 0
    assert found.truncated is False


def test_same_origin_default_skips_external_and_unsupported_links():
    body = b"""
    <a href="https://outside.example/page">Outside</a>
    <a href="mailto:team@example.com">Mail</a>
    <a href="javascript:alert(1)">Script</a>
    <a href="#section">Fragment</a>
    <a href="/safe">Safe</a>
    """

    found = discover_links(
        body,
        base_url="https://example.com/",
        policy=policy(),
    )

    assert found.urls == ("https://example.com/safe",)
    assert found.skipped_external == 1
    assert found.skipped_unsupported == 2


def test_external_links_require_explicit_opt_in():
    found = discover_links(
        b'<a href="https://outside.example/page">Outside</a>',
        base_url="https://example.com/",
        policy=policy(include_external=True),
    )

    assert found.urls == ("https://outside.example/page",)
    assert found.skipped_external == 0


def test_discovery_enforces_unique_link_limit():
    body = "".join(
        f'<a href="/page-{index}">Page</a>' for index in range(5)
    ).encode()

    found = discover_links(
        body,
        base_url="https://example.com/",
        policy=policy(max_links=2),
    )

    assert found.urls == (
        "https://example.com/page-0",
        "https://example.com/page-1",
    )
    assert found.discovered == 5
    assert found.truncated is True


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"max_links": 0}, "max_links"),
        ({"max_links": 501}, "max_links"),
        ({"max_page_bytes": 0}, "max_page_bytes"),
        ({"timeout_seconds": 0}, "timeout_seconds"),
        ({"include_external": "yes"}, "include_external"),
        ({"source_url": "http://127.0.0.1/"}, "non-public"),
    ],
)
def test_policy_rejects_unsafe_or_unbounded_values(changes, message):
    with pytest.raises(SiteWatchError, match=message):
        policy(**changes)


def test_audit_checks_discovered_links_sequentially():
    checked = []

    def check(url, selected):
        checked.append(url)
        return healthy(url, selected)

    result = audit_links(
        policy(),
        fetch_page=lambda selected: HtmlPage(
            final_url=selected.source_url,
            content_type="text/html",
            body=b'<a href="/one">One</a><a href="/two">Two</a>',
        ),
        check_link=check,
    )

    assert checked == [
        "https://example.com/one",
        "https://example.com/two",
    ]
    assert result.healthy is True
    assert result.healthy_count == 2


def test_audit_isolates_source_validation_errors():
    def fail(selected):
        raise SiteWatchError("source page exceeded max_page_bytes")

    result = audit_links(policy(), fetch_page=fail, check_link=healthy)

    assert result.source_error == "source page exceeded max_page_bytes"
    assert result.results == ()
    assert result.healthy is False


def test_non_html_source_is_not_parsed_or_checked():
    called = False

    def check(url, selected):
        nonlocal called
        called = True
        return healthy(url, selected)

    result = audit_links(
        policy(),
        fetch_page=lambda selected: HtmlPage(
            final_url=selected.source_url,
            content_type="application/json",
            body=b'{"href": "/not-a-link"}',
        ),
        check_link=check,
    )

    assert result.source_error == "source page content type is not text/html"
    assert called is False
