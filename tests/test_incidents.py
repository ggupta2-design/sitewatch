from datetime import datetime, timedelta, timezone

from sitewatch.history import AvailabilityHistory, HistorySample
from sitewatch.incidents import analyze_incidents
from sitewatch.models import CheckState


START = datetime(2026, 9, 18, 12, tzinfo=timezone.utc)


def sample(name, minutes, state, *, duration=50):
    return HistorySample(
        name=name,
        checked_at=START + timedelta(minutes=minutes),
        state=state,
        status=200 if state is CheckState.HEALTHY else 503,
        duration_ms=duration,
        error_code="network_error" if state is CheckState.ERROR else None,
    )


def test_incidents_close_only_after_observed_recovery():
    history = AvailabilityHistory(
        (
            sample("API", 0, CheckState.HEALTHY),
            sample("API", 5, CheckState.UNHEALTHY, duration=120),
            sample("API", 10, CheckState.ERROR, duration=300),
            sample("API", 15, CheckState.HEALTHY),
        )
    )

    analysis = analyze_incidents(history)
    incident = analysis.incidents[0]

    assert incident.name == "API"
    assert incident.samples == 2
    assert incident.unhealthy_samples == 1
    assert incident.error_samples == 1
    assert incident.maximum_duration_ms == 300
    assert incident.recovered_at == START + timedelta(minutes=15)
    assert incident.observed_seconds == 600
    assert not incident.open
    assert analysis.healthy


def test_trailing_failures_form_an_open_incident():
    history = AvailabilityHistory(
        (
            sample("Web", 0, CheckState.HEALTHY),
            sample("Web", 5, CheckState.UNHEALTHY),
            sample("Web", 10, CheckState.UNHEALTHY),
        )
    )

    analysis = analyze_incidents(history)
    incident = analysis.incidents[0]

    assert incident.open
    assert incident.recovered_at is None
    assert incident.observed_seconds == 300
    assert analysis.open_count == 1
    assert not analysis.healthy


def test_separate_recoveries_create_separate_incidents():
    history = AvailabilityHistory(
        (
            sample("API", 0, CheckState.ERROR),
            sample("API", 5, CheckState.HEALTHY),
            sample("API", 10, CheckState.UNHEALTHY),
            sample("API", 15, CheckState.HEALTHY),
        )
    )

    analysis = analyze_incidents(history)

    assert analysis.incident_count == 2
    assert analysis.recovered_count == 2
    assert analysis.open_count == 0
    assert analysis.affected_samples == 2
    assert analysis.unhealthy_samples == 1
    assert analysis.error_samples == 1


def test_targets_are_grouped_case_insensitively_and_sorted_deterministically():
    history = AvailabilityHistory(
        (
            sample("Zulu", 5, CheckState.ERROR),
            sample("api", 0, CheckState.UNHEALTHY),
            sample("API", 10, CheckState.HEALTHY),
        )
    )

    analysis = analyze_incidents(history)

    assert [item.name for item in analysis.incidents] == ["api", "Zulu"]
    assert analysis.incidents[0].recovered_at == START + timedelta(minutes=10)


def test_healthy_history_has_no_incidents():
    analysis = analyze_incidents(
        AvailabilityHistory((sample("Web", 0, CheckState.HEALTHY),))
    )

    assert analysis.incidents == ()
    assert analysis.incident_count == 0
    assert analysis.recovered_count == 0
    assert analysis.healthy
