import json

from sitewatch.link_report import format_link_audit, link_audit_to_dict
from sitewatch.links import LinkAudit, LinkResult, LinkState


def audit():
    return LinkAudit(
        source_url="https://private.example/start",
        final_source_url="https://private.example/home",
        results=(
            LinkResult(
                url="https://private.example/ok",
                state=LinkState.HEALTHY,
                status=200,
                final_url="https://private.example/ok",
                duration_ms=4,
            ),
            LinkResult(
                url="https://private.example/missing",
                state=LinkState.BROKEN,
                status=404,
                final_url="https://private.example/missing",
                duration_ms=8,
            ),
        ),
        discovered=5,
        skipped_external=2,
        skipped_unsupported=1,
        truncated=False,
    )


def test_json_report_summarizes_link_health():
    payload = link_audit_to_dict(audit())

    assert payload["healthy"] is False
    assert payload["summary"] == {
        "discovered": 5,
        "checked": 2,
        "healthy": 1,
        "broken": 1,
        "errors": 0,
        "skipped_external": 2,
        "skipped_unsupported": 1,
        "truncated": False,
    }
    assert payload["links"][1]["status"] == 404


def test_url_redaction_removes_source_and_destination_urls():
    content = format_link_audit(audit(), as_json=True, redact_urls=True)
    payload = json.loads(content)

    assert "private.example" not in content
    assert "source_url" not in payload
    assert "url" not in payload["links"][0]
    assert payload["links"][1]["state"] == "broken"


def test_text_report_is_deterministic_and_body_free():
    content = format_link_audit(audit(), redact_urls=True)

    assert content.startswith("SiteWatch link audit\nStatus: attention required")
    assert "Broken: 1" in content
    assert "link-2: broken" in content
    assert "private.example" not in content
    assert "body" not in content.casefold()
    assert content.endswith("\n")


def test_source_error_is_reported_without_links():
    failed = LinkAudit(
        source_url="https://example.com/",
        final_source_url=None,
        results=(),
        discovered=0,
        skipped_external=0,
        skipped_unsupported=0,
        truncated=False,
        source_error="source page request timed out",
    )

    payload = link_audit_to_dict(failed, redact_urls=True)

    assert payload["healthy"] is False
    assert payload["source_error"] == "source page request timed out"
    assert payload["links"] == []
