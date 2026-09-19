import json
from datetime import datetime, timedelta, timezone

from sitewatch.history import AvailabilityHistory, HistorySample
from sitewatch.incident_report import (
    format_incident_analysis,
    incident_analysis_to_dict,
)
from sitewatch.incidents import analyze_incidents
from sitewatch.models import CheckState


START = datetime(2026, 9, 18, 12, tzinfo=timezone.utc)


def sample(minutes, state):
    return HistorySample(
        name="Public API",
        checked_at=START + timedelta(minutes=minutes),
        state=state,
        status=503 if state is not CheckState.HEALTHY else 200,
        duration_ms=125,
        error_code="secret-internal-code" if state is CheckState.ERROR else None,
    )


def analysis():
    return analyze_incidents(
        AvailabilityHistory(
            (
                sample(0, CheckState.UNHEALTHY),
                sample(5, CheckState.ERROR),
                sample(10, CheckState.HEALTHY),
                sample(90, CheckState.HEALTHY),
            )
        ),
        maximum_gap_seconds=3600,
    )


def test_incident_dictionary_contains_aggregate_timeline_metrics():
    payload = incident_analysis_to_dict(analysis())

    assert payload["attention_required"]
    assert payload["summary"] == {
        "incidents": 1,
        "recovered": 1,
        "open": 0,
        "monitoring_gaps": 1,
        "affected_samples": 2,
        "unhealthy_samples": 1,
        "error_samples": 1,
    }
    assert payload["incidents"][0]["recovered_at"] == "2026-09-18T12:10:00Z"
    assert payload["incidents"][0]["observed_seconds"] == 600
    assert payload["monitoring_gaps"][0]["seconds"] == 4800


def test_json_report_is_deterministic_and_omits_sensitive_values():
    report = format_incident_analysis(analysis(), as_json=True)
    payload = json.loads(report)

    assert payload["maximum_gap_seconds"] == 3600
    assert report.endswith("\n")
    assert "https://" not in report
    assert "secret-internal-code" not in report
    assert '"status": 503' not in report


def test_text_report_explains_recovery_and_monitoring_gaps():
    report = format_incident_analysis(analysis())

    assert "Status: attention required" in report
    assert "Public API: recovered, 2 affected samples" in report
    assert "Recovery observed: 2026-09-18T12:10:00Z" in report
    assert "4800 seconds between" in report


def test_clear_report_has_no_detail_sections():
    clear = analyze_incidents(
        AvailabilityHistory((sample(0, CheckState.HEALTHY),)),
        maximum_gap_seconds=3600,
    )

    report = format_incident_analysis(clear)

    assert "Status: clear" in report
    assert "Incidents: 0" in report
    assert "Incident timeline" not in report
    assert "Monitoring gaps\n" not in report
