import json
from datetime import datetime, timedelta, timezone

from sitewatch.availability import summarize_availability
from sitewatch.availability_report import (
    availability_summary_to_dict,
    format_availability_summary,
)
from sitewatch.history import AvailabilityHistory, HistorySample
from sitewatch.models import CheckState


START = datetime(2026, 9, 17, tzinfo=timezone.utc)


def summary():
    history = AvailabilityHistory(
        (
            HistorySample(
                name="private-api",
                checked_at=START,
                state=CheckState.HEALTHY,
                status=200,
                duration_ms=20,
            ),
            HistorySample(
                name="private-api",
                checked_at=START + timedelta(minutes=5),
                state=CheckState.UNHEALTHY,
                status=503,
                duration_ms=40,
            ),
        )
    )
    return summarize_availability(history, minimum_availability=99)


def test_json_summary_contains_goal_and_aggregate_metrics():
    payload = availability_summary_to_dict(summary())

    assert payload["meets_goal"] is False
    assert payload["minimum_availability"] == 99.0
    assert payload["summary"] == {
        "targets": 1,
        "samples": 2,
        "healthy": 1,
        "unhealthy": 1,
        "errors": 0,
        "availability_percent": 50.0,
        "below_goal": 1,
    }
    assert payload["targets"][0]["average_duration_ms"] == 30


def test_summary_contains_no_urls_fingerprints_or_response_content():
    content = format_availability_summary(summary(), as_json=True)

    assert "url" not in content.casefold()
    assert "sha256" not in content
    assert "content_type" not in content
    assert "response" not in content.casefold()
    assert json.loads(content)["targets"][0]["name"] == "private-api"


def test_text_summary_is_deterministic_and_readable():
    content = format_availability_summary(summary())

    assert content.startswith("SiteWatch availability summary\nGoal: 99%")
    assert "Status: below goal" in content
    assert "Availability: 50%" in content
    assert "private-api: 50% (below goal)" in content
    assert "Duration: avg 30 ms, max 40 ms" in content
    assert content.endswith("\n")
