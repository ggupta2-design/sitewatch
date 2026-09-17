from datetime import datetime, timedelta, timezone

import pytest

from sitewatch.availability import summarize_availability
from sitewatch.history import AvailabilityHistory, HistorySample
from sitewatch.models import CheckState
from sitewatch.safety import SiteWatchError


START = datetime(2026, 9, 17, tzinfo=timezone.utc)


def sample(
    name,
    offset,
    state,
    duration,
    *,
    status=200,
    error_code=None,
):
    return HistorySample(
        name=name,
        checked_at=START + timedelta(minutes=offset),
        state=state,
        status=status,
        duration_ms=duration,
        error_code=error_code,
    )


def history():
    return AvailabilityHistory(
        (
            sample("api", 0, CheckState.HEALTHY, 100),
            sample("api", 5, CheckState.HEALTHY, 200),
            sample("api", 10, CheckState.UNHEALTHY, 300, status=503),
            sample("web", 0, CheckState.HEALTHY, 20),
            sample(
                "web",
                5,
                CheckState.ERROR,
                40,
                status=None,
                error_code="timeout",
            ),
        )
    )


def test_summarizes_each_target_deterministically():
    summary = summarize_availability(history(), minimum_availability=60)
    api, web = summary.targets

    assert [target.name for target in summary.targets] == ["api", "web"]
    assert api.samples == 3
    assert api.healthy == 2
    assert api.unhealthy == 1
    assert api.errors == 0
    assert api.availability_percent == 66.667
    assert api.average_duration_ms == 200
    assert api.maximum_duration_ms == 300
    assert api.meets_goal is True
    assert web.availability_percent == 50.0
    assert web.meets_goal is False


def test_summary_reports_weighted_overall_availability():
    summary = summarize_availability(history(), minimum_availability=60)

    assert summary.samples == 5
    assert summary.healthy == 3
    assert summary.unhealthy == 1
    assert summary.errors == 1
    assert summary.availability_percent == 60.0
    assert summary.meets_goal is False
    assert summary.below_goal_count == 1


def test_summary_preserves_observation_window():
    summary = summarize_availability(history(), minimum_availability=0)
    api = summary.targets[0]

    assert api.first_checked_at == START
    assert api.last_checked_at == START + timedelta(minutes=10)


def test_case_variants_are_grouped_as_one_target():
    selected = AvailabilityHistory(
        (
            sample("HomePage", 0, CheckState.HEALTHY, 10),
            sample("homepage", 5, CheckState.HEALTHY, 20),
        )
    )

    summary = summarize_availability(selected)

    assert len(summary.targets) == 1
    assert summary.targets[0].name == "HomePage"
    assert summary.targets[0].samples == 2


@pytest.mark.parametrize("goal", [-0.1, 100.1, True, "99"])
def test_rejects_invalid_availability_goal(goal):
    with pytest.raises(SiteWatchError, match="minimum_availability"):
        summarize_availability(history(), minimum_availability=goal)
