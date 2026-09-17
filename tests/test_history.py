import json
from datetime import datetime, timedelta, timezone

import pytest

from sitewatch.checks import CheckRun
from sitewatch.history import (
    AvailabilityHistory,
    HistorySample,
    append_history,
    format_history,
    history_from_dict,
    history_from_run,
    history_to_dict,
    load_history,
)
from sitewatch.models import CheckResult, CheckState, Observation
from sitewatch.safety import SiteWatchError


START = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)


def result(
    name="homepage",
    *,
    checked_at=START,
    state=CheckState.HEALTHY,
    status=200,
    duration_ms=25,
    error_code=None,
):
    return CheckResult(
        name=name,
        configured_url=f"https://private.example/{name}",
        state=state,
        observation=Observation(
            status=status,
            final_url=f"https://private.example/{name}",
            duration_ms=duration_ms,
            content_type="text/html",
            bytes_read=100,
            sha256="a" * 64,
            checked_at=checked_at,
            error_code=error_code,
        ),
        findings=() if state is CheckState.HEALTHY else ("problem",),
    )


def test_history_captures_availability_metadata_only():
    history = history_from_run(CheckRun((result(),)))
    payload = history_to_dict(history)

    assert payload["schema_version"] == 1
    assert payload["samples"] == [
        {
            "name": "homepage",
            "checked_at": "2026-09-17T12:00:00Z",
            "state": "healthy",
            "status": 200,
            "duration_ms": 25,
            "error_code": None,
        }
    ]
    serialized = format_history(history)
    assert "private.example" not in serialized
    assert "sha256" not in serialized
    assert "content_type" not in serialized
    assert "bytes_read" not in serialized


def test_history_round_trip_is_deterministic(tmp_path):
    history = history_from_run(
        CheckRun((result("zeta"), result("alpha")))
    )
    path = tmp_path / "history.json"
    path.write_text(format_history(history), encoding="utf-8")

    loaded = load_history(path)

    assert loaded == history
    assert [sample.name for sample in loaded.samples] == ["alpha", "zeta"]
    assert format_history(loaded) == format_history(history)


def test_append_returns_new_history_with_later_samples():
    original = history_from_run(CheckRun((result(),)))
    later = CheckRun(
        (result(checked_at=START + timedelta(minutes=5), status=204),)
    )

    combined = append_history(original, later)

    assert len(original.samples) == 1
    assert len(combined.samples) == 2
    assert combined.samples[-1].status == 204


def test_append_rejects_overlapping_or_older_samples():
    original = history_from_run(CheckRun((result(),)))

    with pytest.raises(SiteWatchError, match="later"):
        append_history(original, CheckRun((result(checked_at=START),)))


def test_history_rejects_duplicate_name_and_timestamp():
    sample = HistorySample(
        name="homepage",
        checked_at=START,
        state=CheckState.HEALTHY,
        status=200,
        duration_ms=5,
    )

    with pytest.raises(SiteWatchError, match="unique"):
        AvailabilityHistory(
            (
                sample,
                HistorySample(
                    name="HomePage",
                    checked_at=START,
                    state=CheckState.UNHEALTHY,
                    status=503,
                    duration_ms=8,
                ),
            )
        )


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda data: data.update(extra=True), "exactly"),
        (lambda data: data.update(schema_version=2), "schema_version"),
        (lambda data: data.update(samples=[]), "1 to 10000"),
        (
            lambda data: data["samples"][0].update(checked_at="not-a-time"),
            "ISO timestamp",
        ),
        (
            lambda data: data["samples"][0].update(state="unknown"),
            "state",
        ),
        (
            lambda data: data["samples"][0].update(duration_ms=-1),
            "duration_ms",
        ),
    ],
)
def test_history_rejects_invalid_schema(change, message):
    payload = history_to_dict(history_from_run(CheckRun((result(),))))
    change(payload)

    with pytest.raises(SiteWatchError, match=message):
        history_from_dict(payload)


def test_load_history_hides_invalid_contents(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("private invalid history contents", encoding="utf-8")

    with pytest.raises(SiteWatchError, match="not valid JSON") as error:
        load_history(path)

    assert "private invalid history contents" not in str(error.value)
