from datetime import datetime, timezone

from sitewatch.baseline import baseline_from_run
from sitewatch.checks import CheckRun
from sitewatch.drift import DriftState, compare_to_baseline
from sitewatch.models import CheckResult, CheckState, Observation


def result(
    name,
    *,
    url=None,
    state=CheckState.HEALTHY,
    status=200,
    content_type="text/html",
    digest="a" * 64,
):
    configured_url = url or f"https://example.com/{name}"
    return CheckResult(
        name=name,
        configured_url=configured_url,
        state=state,
        observation=Observation(
            status=status,
            final_url=configured_url,
            duration_ms=10,
            content_type=content_type,
            bytes_read=4,
            sha256=digest,
            checked_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        ),
        findings=() if state is CheckState.HEALTHY else ("unexpected_status",),
    )


def test_comparison_detects_metadata_changes_without_values():
    before = CheckRun((result("homepage"),))
    current = CheckRun(
        (
            result(
                "homepage",
                status=204,
                content_type="application/json",
                digest="b" * 64,
            ),
        )
    )

    comparison = compare_to_baseline(current, baseline_from_run(before))
    item = comparison.results[0]

    assert item.state is DriftState.CHANGED
    assert item.changed_fields == ("status", "content_type", "sha256")
    assert comparison.has_drift is True
    assert comparison.changed_count == 1


def test_comparison_ignores_volatile_observation_metadata():
    before = result("homepage")
    current = CheckResult(
        **{
            **before.__dict__,
            "observation": Observation(
                **{
                    **before.observation.__dict__,
                    "duration_ms": 999,
                    "bytes_read": 999,
                    "checked_at": datetime(2026, 9, 16, tzinfo=timezone.utc),
                }
            ),
        }
    )

    comparison = compare_to_baseline(
        CheckRun((current,)), baseline_from_run(CheckRun((before,)))
    )

    assert comparison.results[0].state is DriftState.UNCHANGED
    assert comparison.has_drift is False
    assert comparison.unchanged_count == 1


def test_comparison_reports_new_and_missing_targets_in_stable_order():
    baseline = baseline_from_run(
        CheckRun((result("alpha"), result("removed")))
    )
    comparison = compare_to_baseline(
        CheckRun((result("alpha"), result("new"))), baseline
    )

    assert [item.name for item in comparison.results] == [
        "alpha",
        "new",
        "removed",
    ]
    assert [item.state for item in comparison.results] == [
        DriftState.UNCHANGED,
        DriftState.NEW,
        DriftState.MISSING,
    ]
    assert comparison.new_count == 1
    assert comparison.missing_count == 1


def test_comparison_matches_names_case_insensitively():
    baseline = baseline_from_run(CheckRun((result("HomePage"),)))
    comparison = compare_to_baseline(
        CheckRun((result("homepage", url="https://example.com/HomePage"),)),
        baseline,
    )

    assert comparison.results[0].state is DriftState.UNCHANGED


def test_unhealthy_current_run_is_recorded_without_manufacturing_drift():
    unhealthy = CheckRun(
        (result("homepage", state=CheckState.UNHEALTHY, status=503),)
    )
    baseline = baseline_from_run(unhealthy)

    comparison = compare_to_baseline(unhealthy, baseline)

    assert comparison.current_healthy is False
    assert comparison.has_drift is False
