import json

from sitewatch.cli import run
from sitewatch.links import LinkAudit, LinkResult, LinkState


def sample_audit(*, state=LinkState.HEALTHY):
    result = LinkResult(
        url="https://example.com/about",
        state=state,
        status=200 if state is LinkState.HEALTHY else 404,
        final_url="https://example.com/about",
        duration_ms=5,
        error_code=None,
    )
    return LinkAudit(
        source_url="https://example.com/",
        final_source_url="https://example.com/",
        results=(result,),
        discovered=1,
        skipped_external=0,
        skipped_unsupported=0,
        truncated=False,
    )


def test_links_command_passes_explicit_bounds(capsys, monkeypatch):
    captured = {}

    def fake_audit(selected, **kwargs):
        captured["policy"] = selected
        return sample_audit()

    monkeypatch.setattr("sitewatch.cli.audit_links", fake_audit)

    code = run(
        [
            "links",
            "https://example.com/",
            "--max-links",
            "12",
            "--max-page-bytes",
            "4096",
            "--timeout-seconds",
            "3.5",
            "--include-external",
            "--json",
        ]
    )

    assert code == 0
    assert json.loads(capsys.readouterr().out)["healthy"] is True
    selected = captured["policy"]
    assert selected.max_links == 12
    assert selected.max_page_bytes == 4096
    assert selected.timeout_seconds == 3.5
    assert selected.include_external is True


def test_links_command_signals_broken_destinations(capsys, monkeypatch):
    monkeypatch.setattr(
        "sitewatch.cli.audit_links",
        lambda selected, **kwargs: sample_audit(state=LinkState.BROKEN),
    )

    assert run(["links", "https://example.com/", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["healthy"] is False
    assert payload["summary"]["broken"] == 1


def test_links_command_redacts_all_urls(capsys, monkeypatch):
    monkeypatch.setattr(
        "sitewatch.cli.audit_links",
        lambda selected, **kwargs: sample_audit(),
    )

    assert run(
        ["links", "https://example.com/", "--json", "--redact-urls"]
    ) == 0
    content = capsys.readouterr().out

    assert "example.com" not in content
    assert "source_url" not in json.loads(content)


def test_links_command_exports_without_overwriting(
    tmp_path, capsys, monkeypatch
):
    output = tmp_path / "reports" / "links.json"
    monkeypatch.setattr(
        "sitewatch.cli.audit_links",
        lambda selected, **kwargs: sample_audit(),
    )
    command = [
        "links",
        "https://example.com/",
        "--json",
        "--output",
        str(output),
    ]

    assert run(command) == 0
    assert capsys.readouterr().out == "Wrote links.json\n"
    assert json.loads(output.read_text(encoding="utf-8"))["healthy"] is True

    assert run(command) == 2
    assert "already exists" in capsys.readouterr().err


def test_links_command_rejects_unsafe_url_without_network(capsys):
    assert run(["links", "http://127.0.0.1/"]) == 2

    assert "non-public" in capsys.readouterr().err


def test_links_command_rejects_invalid_limits(capsys):
    assert run(
        ["links", "https://example.com/", "--max-links", "0"]
    ) == 2

    assert "max_links" in capsys.readouterr().err
