import json

import pytest

from sitewatch.reliability_policy import (
    ReliabilityPolicy,
    format_policy,
    load_policy,
    policy_from_dict,
    policy_to_dict,
)


def payload(**overrides):
    values = {
        "schema_version": 1,
        "name": "production baseline",
        "minimum_availability": 99.5,
        "maximum_open_incidents": 0,
        "maximum_monitoring_gaps": 1,
        "maximum_errors": 2,
        "maximum_gap_seconds": 900,
    }
    values.update(overrides)
    return values


def test_policy_round_trip_is_strict_and_deterministic(tmp_path):
    policy = policy_from_dict(payload())
    path = tmp_path / "policy.json"
    path.write_text(format_policy(policy), encoding="utf-8")

    loaded = load_policy(path)

    assert loaded == policy
    assert policy_to_dict(loaded) == payload()
    assert format_policy(loaded).endswith("\n")


def test_policy_normalizes_name_and_numeric_availability():
    policy = ReliabilityPolicy(
        name="  launch readiness  ",
        minimum_availability=99,
        maximum_open_incidents=0,
        maximum_monitoring_gaps=0,
        maximum_errors=0,
        maximum_gap_seconds=3600,
    )

    assert policy.name == "launch readiness"
    assert policy.minimum_availability == 99.0


@pytest.mark.parametrize(
    "change, message",
    [
        ({"name": ""}, "policy name"),
        ({"minimum_availability": 101}, "minimum_availability"),
        ({"maximum_open_incidents": -1}, "maximum_open_incidents"),
        ({"maximum_monitoring_gaps": True}, "maximum_monitoring_gaps"),
        ({"maximum_errors": 10_001}, "maximum_errors"),
        ({"maximum_gap_seconds": 0}, "maximum_gap_seconds"),
        ({"maximum_gap_seconds": 31_536_001}, "maximum_gap_seconds"),
    ],
)
def test_policy_rejects_values_outside_bounds(change, message):
    with pytest.raises(ValueError, match=message):
        policy_from_dict(payload(**change))


def test_policy_rejects_unknown_or_missing_fields():
    unknown = payload(extra=True)
    missing = payload()
    missing.pop("maximum_errors")

    with pytest.raises(ValueError, match="exactly"):
        policy_from_dict(unknown)
    with pytest.raises(ValueError, match="exactly"):
        policy_from_dict(missing)


def test_policy_rejects_unsupported_version_and_invalid_files(tmp_path):
    with pytest.raises(ValueError, match="schema_version"):
        policy_from_dict(payload(schema_version=2))

    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="valid JSON"):
        load_policy(broken)

    with pytest.raises(ValueError, match="does not exist"):
        load_policy(tmp_path / "missing.json")
