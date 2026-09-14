import json
from datetime import datetime, timezone

from sitewatch.checks import CheckRun
from sitewatch.models import CheckResult, CheckState, Observation
from sitewatch.report import check_run_to_dict, format_check_run


def run():
    observation = Observation(
        status=200,
        final_url="https://example.com/final",
        duration_ms=42,
        content_type="text/html",
        bytes_read=123,
        sha256="a" * 64,
        checked_at=datetime(2026, 9, 14, tzinfo=timezone.utc),
    )
    return CheckRun(
        (
            CheckResult(
                name="homepage",
                configured_url="https://example.com/",
                state=CheckState.HEALTHY,
                observation=observation,
            ),
        )
    )


def test_formats_stable_json_report():
    output = format_check_run(run(), as_json=True)
    payload = json.loads(output)

    assert payload["healthy"] is True
    assert payload["summary"] == {"targets": 1, "healthy": 1, "unhealthy": 0}
    assert payload["targets"][0]["status"] == 200
    assert payload["targets"][0]["checked_at"] == "2026-09-14T00:00:00Z"
    assert "body" not in payload["targets"][0]


def test_formats_readable_health_report():
    output = format_check_run(run())

    assert output.startswith("SiteWatch health check")
    assert "homepage: healthy" in output
    assert "Status: 200" in output
    assert "Findings: none" in output


def test_redacts_configured_and_final_urls():
    output = format_check_run(run(), as_json=True, redact_urls=True)
    payload = check_run_to_dict(run(), redact_urls=True)

    assert "configured_url" not in payload["targets"][0]
    assert "final_url" not in payload["targets"][0]
    assert "example.com" not in output
    assert "a" * 64 in output
