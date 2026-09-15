import json

from sitewatch.cli import run
from test_cli import fake_run, write_config


def write_baseline(tmp_path, *, digest="a" * 64):
    path = tmp_path / "baseline.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "targets": [
                    {
                        "name": "homepage",
                        "configured_url": "https://example.com/health",
                        "state": "healthy",
                        "status": 200,
                        "content_type": "text/plain",
                        "sha256": digest,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_snapshot_creates_body_free_non_overwriting_baseline(
    tmp_path, capsys, monkeypatch
):
    config = write_config(tmp_path)
    output = tmp_path / "snapshots" / "baseline.json"
    monkeypatch.setattr("sitewatch.cli.run_checks", lambda targets: fake_run())

    command = ["snapshot", str(config), "--output", str(output)]
    assert run(command) == 0
    assert capsys.readouterr().out == "Wrote baseline.json\n"

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["targets"][0]["sha256"] == "a" * 64
    assert "duration_ms" not in payload["targets"][0]
    assert run(command) == 2
    assert "already exists" in capsys.readouterr().err


def test_compare_returns_zero_for_unchanged_healthy_run(
    tmp_path, capsys, monkeypatch
):
    config = write_config(tmp_path)
    baseline = write_baseline(tmp_path)
    monkeypatch.setattr("sitewatch.cli.run_checks", lambda targets: fake_run())

    assert run(["compare", str(config), str(baseline), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["drift"] is False
    assert payload["current_healthy"] is True
    assert payload["summary"]["unchanged"] == 1


def test_compare_signals_drift_and_redacts_urls(
    tmp_path, capsys, monkeypatch
):
    config = write_config(tmp_path)
    baseline = write_baseline(tmp_path, digest="b" * 64)
    monkeypatch.setattr("sitewatch.cli.run_checks", lambda targets: fake_run())

    command = [
        "compare",
        str(config),
        str(baseline),
        "--json",
        "--redact-urls",
    ]
    assert run(command) == 1
    content = capsys.readouterr().out
    payload = json.loads(content)

    assert payload["drift"] is True
    assert payload["targets"][0]["changed_fields"] == ["sha256"]
    assert "example.com" not in content


def test_compare_exports_without_overwriting(tmp_path, capsys, monkeypatch):
    config = write_config(tmp_path)
    baseline = write_baseline(tmp_path)
    output = tmp_path / "reports" / "changes.json"
    monkeypatch.setattr("sitewatch.cli.run_checks", lambda targets: fake_run())

    command = [
        "compare",
        str(config),
        str(baseline),
        "--json",
        "--output",
        str(output),
    ]
    assert run(command) == 0
    assert capsys.readouterr().out == "Wrote changes.json\n"
    assert json.loads(output.read_text(encoding="utf-8"))["drift"] is False

    assert run(command) == 2
    assert "already exists" in capsys.readouterr().err


def test_validate_baseline_never_runs_network_checks(
    tmp_path, capsys, monkeypatch
):
    baseline = write_baseline(tmp_path)

    def forbidden(targets):
        raise AssertionError("network checks must not run")

    monkeypatch.setattr("sitewatch.cli.run_checks", forbidden)

    assert run(["validate-baseline", str(baseline), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "valid": True,
        "targets": 1,
        "names": ["homepage"],
    }


def test_invalid_baseline_returns_invalid_input_status(
    tmp_path, capsys, monkeypatch
):
    config = write_config(tmp_path)
    baseline = tmp_path / "invalid.json"
    baseline.write_text("private bad baseline", encoding="utf-8")
    monkeypatch.setattr("sitewatch.cli.run_checks", lambda targets: fake_run())

    assert run(["compare", str(config), str(baseline)]) == 2
    output = capsys.readouterr()

    assert "not valid JSON" in output.err
    assert "private bad baseline" not in output.err
