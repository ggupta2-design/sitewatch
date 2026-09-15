import json
from datetime import datetime, timezone

import pytest

from sitewatch.baseline import (
    Baseline,
    BaselineEntry,
    baseline_from_dict,
    baseline_from_run,
    baseline_to_dict,
    format_baseline,
    load_baseline,
)
from sitewatch.checks import CheckRun
from sitewatch.models import CheckResult, CheckState, Observation
from sitewatch.safety import SiteWatchError


def sample_run():
    observation = Observation(
        status=200,
        final_url="https://example.com/",
        duration_ms=12,
        content_type="Text/HTML",
        bytes_read=4,
        sha256="a" * 64,
        checked_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
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


def test_baseline_captures_stable_metadata_only():
    baseline = baseline_from_run(sample_run())
    payload = baseline_to_dict(baseline)

    assert payload["schema_version"] == 1
    assert payload["targets"] == [
        {
            "name": "homepage",
            "configured_url": "https://example.com/",
            "state": "healthy",
            "status": 200,
            "content_type": "text/html",
            "sha256": "a" * 64,
        }
    ]
    serialized = format_baseline(baseline)
    assert "duration_ms" not in serialized
    assert "bytes_read" not in serialized
    assert "checked_at" not in serialized


def test_baseline_round_trip_is_deterministic(tmp_path):
    baseline = baseline_from_run(sample_run())
    path = tmp_path / "baseline.json"
    path.write_text(format_baseline(baseline), encoding="utf-8")

    loaded = load_baseline(path)

    assert loaded == baseline
    assert format_baseline(loaded) == format_baseline(baseline)


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda data: data.update(extra=True), "exactly"),
        (lambda data: data.update(schema_version=2), "schema_version"),
        (lambda data: data.update(targets=[]), "1 to 100"),
        (
            lambda data: data["targets"][0].update(sha256="NOT-A-DIGEST"),
            "sha256",
        ),
        (
            lambda data: data["targets"][0].update(status=True),
            "status",
        ),
        (
            lambda data: data["targets"][0].update(state="unknown"),
            "state",
        ),
    ],
)
def test_baseline_rejects_invalid_schema(change, message):
    payload = baseline_to_dict(baseline_from_run(sample_run()))
    change(payload)

    with pytest.raises(SiteWatchError, match=message):
        baseline_from_dict(payload)


def test_baseline_rejects_duplicate_names():
    entry = BaselineEntry(
        name="homepage",
        configured_url="https://example.com/",
        state=CheckState.HEALTHY,
        status=200,
        content_type="text/html",
        sha256="a" * 64,
    )

    with pytest.raises(SiteWatchError, match="unique"):
        Baseline((entry, BaselineEntry(**{**entry.__dict__, "name": "HomePage"})))


def test_load_baseline_hides_invalid_contents(tmp_path):
    path = tmp_path / "baseline.json"
    path.write_text("private invalid baseline contents", encoding="utf-8")

    with pytest.raises(SiteWatchError, match="not valid JSON") as error:
        load_baseline(path)

    assert "private invalid baseline contents" not in str(error.value)
