from datetime import datetime, timezone

from sitewatch.checks import evaluate_observation, run_checks
from sitewatch.models import CheckState, Observation, Target


def observation(**changes):
    values = {
        "status": 200,
        "final_url": "https://example.com/",
        "duration_ms": 25,
        "content_type": "text/html",
        "bytes_read": 20,
        "sha256": "a" * 64,
        "checked_at": datetime(2026, 9, 14, tzinfo=timezone.utc),
        "error_code": None,
    }
    values.update(changes)
    return Observation(**values)


def target(**changes):
    values = {
        "name": "homepage",
        "url": "https://example.com/",
        "expected_content_type": "text/html",
    }
    values.update(changes)
    return Target(**values)


def test_evaluates_healthy_response():
    result = evaluate_observation(target(), observation())

    assert result.healthy is True
    assert result.state is CheckState.HEALTHY
    assert result.findings == ()


def test_evaluates_response_rule_failures_deterministically():
    result = evaluate_observation(
        target(),
        observation(
            status=503,
            final_url="https://example.com/login",
            content_type="application/json",
        ),
    )

    assert result.state is CheckState.UNHEALTHY
    assert result.findings == (
        "unexpected_content_type",
        "unexpected_redirect",
        "unexpected_status",
    )


def test_transport_error_takes_error_state():
    result = evaluate_observation(
        target(),
        observation(status=None, final_url=None, error_code="timeout"),
    )

    assert result.state is CheckState.ERROR
    assert result.findings == ("timeout",)


def test_runs_checks_in_configuration_order():
    targets = (target(name="first"), target(name="second"))

    def observer(item):
        status = 200 if item.name == "first" else 500
        return observation(status=status)

    run = run_checks(targets, observer=observer)

    assert [item.name for item in run.results] == ["first", "second"]
    assert run.healthy is False
    assert run.healthy_count == 1
    assert run.unhealthy_count == 1
