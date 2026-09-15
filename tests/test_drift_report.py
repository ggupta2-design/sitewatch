import json

from sitewatch.drift import DriftResult, DriftRun, DriftState
from sitewatch.drift_report import drift_run_to_dict, format_drift_run


def comparison():
    return DriftRun(
        (
            DriftResult(
                name="homepage",
                state=DriftState.CHANGED,
                changed_fields=("status", "sha256"),
                configured_url="https://private.example/health",
            ),
            DriftResult(
                name="new-target",
                state=DriftState.NEW,
                changed_fields=("target",),
                configured_url="https://private.example/new",
            ),
        ),
        current_healthy=False,
    )


def test_json_drift_report_contains_counts_and_field_names_only():
    payload = drift_run_to_dict(comparison())

    assert payload["drift"] is True
    assert payload["current_healthy"] is False
    assert payload["summary"] == {
        "targets": 2,
        "unchanged": 0,
        "changed": 1,
        "new": 1,
        "missing": 0,
    }
    assert payload["targets"][0]["changed_fields"] == ["status", "sha256"]
    assert "before" not in json.dumps(payload)
    assert "after" not in json.dumps(payload)


def test_url_redaction_removes_all_configured_urls():
    content = format_drift_run(
        comparison(), as_json=True, redact_urls=True
    )
    payload = json.loads(content)

    assert "private.example" not in content
    assert "configured_url" not in payload["targets"][0]
    assert payload["targets"][0]["name"] == "homepage"


def test_text_report_is_deterministic_and_value_free():
    content = format_drift_run(comparison(), redact_urls=True)

    assert content.startswith("SiteWatch baseline comparison\nStatus: changed")
    assert "Current health: unhealthy" in content
    assert "homepage: changed" in content
    assert "Changed fields: status, sha256" in content
    assert "503" not in content
    assert content.endswith("\n")
