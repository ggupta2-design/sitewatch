import json

from sitewatch.cli import run
from test_cli import fake_run, write_config


def write_history(tmp_path, *, include_failure=False):
    samples = [
        {
            "name": "homepage",
            "checked_at": "2026-09-13T00:00:00Z",
            "state": "healthy",
            "status": 200,
            "duration_ms": 20,
            "error_code": None,
        }
    ]
    if include_failure:
        samples.append(
            {
                "name": "homepage",
                "checked_at": "2026-09-13T01:00:00Z",
                "state": "unhealthy",
                "status": 503,
                "duration_ms": 40,
                "error_code": None,
            }
        )
    path = tmp_path / "history.json"
    path.write_text(
        json.dumps({"schema_version": 1, "samples": samples}),
        encoding="utf-8",
    )
    return path


def test_history_create_writes_private_metadata_only(
    tmp_path, capsys, monkeypatch
):
    config = write_config(tmp_path)
    output = tmp_path / "history" / "first.json"
    monkeypatch.setattr("sitewatch.cli.run_checks", lambda targets: fake_run())

    command = ["history-create", str(config), "--output", str(output)]
    assert run(command) == 0
    assert capsys.readouterr().out == "Wrote first.json\n"

    content = output.read_text(encoding="utf-8")
    payload = json.loads(content)
    assert len(payload["samples"]) == 1
    assert "example.com" not in content
    assert "sha256" not in content

    assert run(command) == 2
    assert "already exists" in capsys.readouterr().err


def test_history_append_writes_new_file_and_preserves_input(
    tmp_path, capsys, monkeypatch
):
    config = write_config(tmp_path)
    original = write_history(tmp_path)
    original_content = original.read_text(encoding="utf-8")
    output = tmp_path / "next-history.json"
    monkeypatch.setattr("sitewatch.cli.run_checks", lambda targets: fake_run())

    assert run(
        [
            "history-append",
            str(config),
            str(original),
            "--output",
            str(output),
        ]
    ) == 0

    assert capsys.readouterr().out == "Wrote next-history.json\n"
    assert original.read_text(encoding="utf-8") == original_content
    assert len(json.loads(output.read_text(encoding="utf-8"))["samples"]) == 2


def test_history_validate_never_runs_network_checks(
    tmp_path, capsys, monkeypatch
):
    history = write_history(tmp_path)

    def forbidden(targets):
        raise AssertionError("network checks must not run")

    monkeypatch.setattr("sitewatch.cli.run_checks", forbidden)

    assert run(["history-validate", str(history), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload == {
        "valid": True,
        "samples": 1,
        "targets": 1,
        "names": ["homepage"],
    }


def test_availability_summary_is_local_and_signals_missed_goal(
    tmp_path, capsys, monkeypatch
):
    history = write_history(tmp_path, include_failure=True)

    def forbidden(targets):
        raise AssertionError("network checks must not run")

    monkeypatch.setattr("sitewatch.cli.run_checks", forbidden)

    assert run(
        [
            "availability",
            str(history),
            "--minimum-availability",
            "99",
            "--json",
        ]
    ) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["meets_goal"] is False
    assert payload["summary"]["availability_percent"] == 50.0
    assert payload["targets"][0]["name"] == "homepage"


def test_availability_summary_exports_without_overwriting(
    tmp_path, capsys
):
    history = write_history(tmp_path)
    output = tmp_path / "reports" / "availability.json"
    command = [
        "availability",
        str(history),
        "--minimum-availability",
        "99",
        "--json",
        "--output",
        str(output),
    ]

    assert run(command) == 0
    assert capsys.readouterr().out == "Wrote availability.json\n"
    assert json.loads(output.read_text(encoding="utf-8"))["meets_goal"] is True

    assert run(command) == 2
    assert "already exists" in capsys.readouterr().err


def test_availability_rejects_invalid_goal(tmp_path, capsys):
    history = write_history(tmp_path)

    assert run(
        [
            "availability",
            str(history),
            "--minimum-availability",
            "101",
        ]
    ) == 2

    assert "minimum_availability" in capsys.readouterr().err
