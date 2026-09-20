from datetime import datetime, timedelta, timezone

from sitewatch.history import AvailabilityHistory, HistorySample
from sitewatch.models import CheckState
from sitewatch.reliability import evaluate_reliability
from sitewatch.reliability_policy import ReliabilityPolicy


START = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)


def sample(name, minutes, state):
    return HistorySample(
        name=name,
        checked_at=START + timedelta(minutes=minutes),
        state=state,
        status=200 if state is CheckState.HEALTHY else None,
        duration_ms=50,
        error_code="network_error" if state is CheckState.ERROR else None,
    )


def policy(**overrides):
    values = {
        "name": "default",
        "minimum_availability": 50,
        "maximum_open_incidents": 0,
        "maximum_monitoring_gaps": 0,
        "maximum_errors": 0,
        "maximum_gap_seconds": 3600,
    }
    values.update(overrides)
    return ReliabilityPolicy(**values)


def test_healthy_history_produces_clear_decision():
    history = AvailabilityHistory(
        (
            sample("API", 0, CheckState.HEALTHY),
            sample("API", 10, CheckState.HEALTHY),
        )
    )

    decision = evaluate_reliability(history, policy())

    assert not decision.alert
    assert decision.finding_codes == ()
    assert decision.failed_checks == 0
    assert decision.samples == 2
    assert decision.targets == 1
    assert all(check.passed for check in decision.checks)


def test_each_policy_failure_has_a_stable_code():
    history = AvailabilityHistory(
        (
            sample("API", 0, CheckState.HEALTHY),
            sample("API", 120, CheckState.ERROR),
        )
    )

    decision = evaluate_reliability(
        history,
        policy(minimum_availability=75),
    )

    assert decision.alert
    assert decision.finding_codes == (
        "availability_below_minimum",
        "open_incidents_exceeded",
        "monitoring_gaps_exceeded",
        "errors_exceeded",
    )
    assert decision.failed_checks == 4


def test_availability_uses_worst_target_not_masked_portfolio_average():
    history = AvailabilityHistory(
        (
            sample("Healthy API", 0, CheckState.HEALTHY),
            sample("Healthy API", 5, CheckState.HEALTHY),
            sample("Weak API", 0, CheckState.ERROR),
            sample("Weak API", 5, CheckState.HEALTHY),
        )
    )

    decision = evaluate_reliability(
        history,
        policy(minimum_availability=75, maximum_errors=1),
    )
    availability = decision.checks[0]

    assert availability.observed == 50.0
    assert availability.limit == 75.0
    assert not availability.passed
    assert decision.finding_codes == ("availability_below_minimum",)


def test_policy_thresholds_are_inclusive():
    history = AvailabilityHistory(
        (
            sample("API", 0, CheckState.HEALTHY),
            sample("API", 120, CheckState.ERROR),
        )
    )

    decision = evaluate_reliability(
        history,
        policy(
            minimum_availability=50,
            maximum_open_incidents=1,
            maximum_monitoring_gaps=1,
            maximum_errors=1,
        ),
    )

    assert not decision.alert
