import json

from sitewatch.cli import run
from test_policy_cli import write_policy


def write_history(tmp_path, states):
    samples = []
    for index, state in enumerate(states):
        samples.append(
            {
                "name": "homepage",
                "checked_at": f"2026-09-20T00:{index * 5:02d}:00Z",
                "state": state,
                "status": 200 if state == "healthy" else None,
                "duration_ms": 25,
                "error_code": "network_error" if state == "error" else None,
            }
        )
    path = tmp_path / "history.json"
    path.write_text(
        json.dumps({"schema_version": 1, "samples": samples}),
        encoding="utf-8",
    )
    return path


def test_policy_check_is_local_and_signals_alert(tmp_path, capsys, monkeypatch):
    history = write_history(tmp_path, ["healthy", "error"])
    policy = write_policy(
        tmp_path,
        minimum_availability=99,
        maximum_open_incidents=0,
        maximum_errors=0,
    )

    def forbidden(targets):
        raise AssertionError("network checks must not run")

    monkeypatch.setattr("sitewatch.cli.run_checks", forbidden)

    assert run(["policy-check", str(history), str(policy), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["alert"] is True
    assert payload["finding_codes"] == [
        "availability_below_minimum",
        "open_incidents_exceeded",
        "errors_exceeded",
    ]


def test_policy_check_clear_decision_returns_success(tmp_path, capsys):
    history = write_history(tmp_path, ["healthy", "healthy"])
    policy = write_policy(tmp_path)

    assert run(["policy-check", str(history), str(policy), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["alert"] is False
    assert payload["summary"]["failed_checks"] == 0


def test_policy_check_exports_without_overwriting(tmp_path, capsys):
    history = write_history(tmp_path, ["healthy"])
    policy = write_policy(tmp_path)
    output = tmp_path / "reports" / "decision.json"
    command = [
        "policy-check",
        str(history),
        str(policy),
        "--json",
        "--output",
        str(output),
    ]

    assert run(command) == 0
    assert capsys.readouterr().out == "Wrote decision.json\n"
    assert json.loads(output.read_text(encoding="utf-8"))["alert"] is False

    assert run(command) == 2
    assert "already exists" in capsys.readouterr().err


def test_policy_check_rejects_invalid_history_or_policy(tmp_path, capsys):
    policy = write_policy(tmp_path)
    bad_history = tmp_path / "bad-history.json"
    bad_history.write_text("{}", encoding="utf-8")

    assert run(["policy-check", str(bad_history), str(policy)]) == 2
    assert "history" in capsys.readouterr().err
