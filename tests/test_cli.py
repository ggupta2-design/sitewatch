import json
from datetime import datetime, timezone

from sitewatch.checks import CheckRun
from sitewatch.cli import run
from sitewatch.models import CheckResult, CheckState, Observation


def write_config(tmp_path):
    path = tmp_path / "targets.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "targets": [
                    {
                        "name": "homepage",
                        "url": "https://example.com/health",
                        "expected_statuses": [200],
                        "timeout_seconds": 5,
                        "max_bytes": 10000,
                        "expected_content_type": "text/plain",
                        "allow_redirects": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def fake_run(state=CheckState.HEALTHY):
    observation = Observation(
        status=200 if state is CheckState.HEALTHY else 503,
        final_url="https://example.com/health",
        duration_ms=10,
        content_type="text/plain",
        bytes_read=2,
        sha256="a" * 64,
        checked_at=datetime(2026, 9, 14, tzinfo=timezone.utc),
    )
    return CheckRun(
        (
            CheckResult(
                name="homepage",
                configured_url="https://example.com/health",
                state=state,
                observation=observation,
                findings=() if state is CheckState.HEALTHY else ("unexpected_status",),
            ),
        )
    )


def test_validate_command_makes_no_checks(tmp_path, capsys, monkeypatch):
    config = write_config(tmp_path)

    def forbidden(targets):
        raise AssertionError("network checks must not run")

    monkeypatch.setattr("sitewatch.cli.run_checks", forbidden)

    assert run(["validate", str(config), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload == {"valid": True, "targets": 1, "names": ["homepage"]}


def test_check_command_returns_healthy_status(tmp_path, capsys, monkeypatch):
    config = write_config(tmp_path)
    monkeypatch.setattr("sitewatch.cli.run_checks", lambda targets: fake_run())

    assert run(["check", str(config), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["healthy"] is True
    assert payload["summary"]["healthy"] == 1


def test_check_command_signals_unhealthy_result(tmp_path, capsys, monkeypatch):
    config = write_config(tmp_path)
    monkeypatch.setattr(
        "sitewatch.cli.run_checks",
        lambda targets: fake_run(CheckState.UNHEALTHY),
    )

    assert run(["check", str(config), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["healthy"] is False
    assert payload["targets"][0]["findings"] == ["unexpected_status"]


def test_check_exports_redacted_report_without_overwrite(
    tmp_path, capsys, monkeypatch
):
    config = write_config(tmp_path)
    output = tmp_path / "reports" / "health.json"
    monkeypatch.setattr("sitewatch.cli.run_checks", lambda targets: fake_run())
    command = [
        "check",
        str(config),
        "--json",
        "--redact-urls",
        "--output",
        str(output),
    ]

    assert run(command) == 0
    assert capsys.readouterr().out == "Wrote health.json\n"
    content = output.read_text(encoding="utf-8")
    assert "example.com" not in content

    assert run(command) == 2
    assert "already exists" in capsys.readouterr().err


def test_cli_reports_invalid_config_without_traceback(tmp_path, capsys):
    config = tmp_path / "bad.json"
    config.write_text("private invalid content", encoding="utf-8")

    assert run(["validate", str(config)]) == 2
    output = capsys.readouterr()

    assert "not valid JSON" in output.err
    assert "private invalid content" not in output.err
