import json

from sitewatch.cli import run


def write_history(tmp_path, samples):
    path = tmp_path / "history.json"
    path.write_text(
        json.dumps({"schema_version": 1, "samples": samples}),
        encoding="utf-8",
    )
    return path


def item(time, state):
    return {
        "name": "homepage",
        "checked_at": time,
        "state": state,
        "status": 200 if state == "healthy" else 503,
        "duration_ms": 40,
        "error_code": None,
    }


def test_incident_command_is_local_and_reports_recovery(tmp_path, capsys, monkeypatch):
    history = write_history(
        tmp_path,
        [
            item("2026-09-18T00:00:00Z", "unhealthy"),
            item("2026-09-18T00:05:00Z", "healthy"),
        ],
    )

    def forbidden(targets):
        raise AssertionError("network checks must not run")

    monkeypatch.setattr("sitewatch.cli.run_checks", forbidden)

    assert run(["incidents", str(history), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["incidents"] == 1
    assert payload["summary"]["recovered"] == 1
    assert payload["summary"]["open"] == 0


def test_incident_command_signals_open_incidents_and_gaps(tmp_path, capsys):
    history = write_history(
        tmp_path,
        [
            item("2026-09-18T00:00:00Z", "healthy"),
            item("2026-09-18T02:00:00Z", "unhealthy"),
        ],
    )

    assert run(
        [
            "incidents",
            str(history),
            "--maximum-gap-seconds",
            "3600",
            "--json",
        ]
    ) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["attention_required"]
    assert payload["summary"]["open"] == 1
    assert payload["summary"]["monitoring_gaps"] == 1


def test_incident_report_export_is_non_overwriting(tmp_path, capsys):
    history = write_history(
        tmp_path, [item("2026-09-18T00:00:00Z", "healthy")]
    )
    output = tmp_path / "reports" / "incidents.json"
    command = [
        "incidents",
        str(history),
        "--json",
        "--output",
        str(output),
    ]

    assert run(command) == 0
    assert capsys.readouterr().out == "Wrote incidents.json\n"
    assert json.loads(output.read_text(encoding="utf-8"))["attention_required"] is False

    assert run(command) == 2
    assert "already exists" in capsys.readouterr().err


def test_incident_command_rejects_invalid_gap_limit(tmp_path, capsys):
    history = write_history(
        tmp_path, [item("2026-09-18T00:00:00Z", "healthy")]
    )

    assert run(
        ["incidents", str(history), "--maximum-gap-seconds", "0"]
    ) == 2
    assert "maximum_gap_seconds" in capsys.readouterr().err
