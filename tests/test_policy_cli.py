import json

from sitewatch.cli import run


def write_policy(tmp_path, **overrides):
    payload = {
        "schema_version": 1,
        "name": "production",
        "minimum_availability": 99.0,
        "maximum_open_incidents": 0,
        "maximum_monitoring_gaps": 0,
        "maximum_errors": 0,
        "maximum_gap_seconds": 900,
    }
    payload.update(overrides)
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_policy_validation_is_local_and_machine_readable(
    tmp_path, capsys, monkeypatch
):
    policy = write_policy(tmp_path)

    def forbidden(targets):
        raise AssertionError("network checks must not run")

    monkeypatch.setattr("sitewatch.cli.run_checks", forbidden)

    assert run(["policy-validate", str(policy), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["valid"] is True
    assert payload["name"] == "production"
    assert payload["maximum_gap_seconds"] == 900


def test_policy_validation_has_readable_output(tmp_path, capsys):
    policy = write_policy(tmp_path)

    assert run(["policy-validate", str(policy)]) == 0
    output = capsys.readouterr().out

    assert "SiteWatch reliability policy is valid" in output
    assert "Minimum availability: 99%" in output
    assert "Maximum gap: 900 seconds" in output


def test_policy_validation_rejects_invalid_thresholds(tmp_path, capsys):
    policy = write_policy(tmp_path, maximum_errors=-1)

    assert run(["policy-validate", str(policy)]) == 2
    assert "maximum_errors" in capsys.readouterr().err
