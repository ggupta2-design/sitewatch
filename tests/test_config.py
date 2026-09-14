import json

import pytest

from sitewatch.config import config_from_dict, load_config
from sitewatch.safety import SiteWatchError


def target(name="homepage"):
    return {
        "name": name,
        "url": "https://example.com/health",
        "expected_statuses": [200, 204],
        "timeout_seconds": 5,
        "max_bytes": 100000,
        "expected_content_type": "text/html",
        "allow_redirects": False,
    }


def test_loads_strict_versioned_configuration(tmp_path):
    path = tmp_path / "targets.json"
    path.write_text(
        json.dumps({"schema_version": 1, "targets": [target()]}),
        encoding="utf-8",
    )

    targets = load_config(path)

    assert len(targets) == 1
    assert targets[0].name == "homepage"
    assert targets[0].expected_statuses == (200, 204)


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"schema_version": 2, "targets": [target()]}, "schema_version"),
        ({"schema_version": 1, "targets": []}, "1 to 100"),
        ({"schema_version": 1, "targets": "bad"}, "must be a list"),
        (
            {"schema_version": 1, "targets": [target()], "secret": "x"},
            "exactly",
        ),
    ],
)
def test_rejects_invalid_configuration_shapes(payload, message):
    with pytest.raises(SiteWatchError, match=message):
        config_from_dict(payload)


def test_rejects_unknown_target_fields_without_echoing_values():
    payload = target()
    payload["token"] = "do-not-print-this"

    with pytest.raises(SiteWatchError) as error:
        config_from_dict({"schema_version": 1, "targets": [payload]})

    assert "supported fields" in str(error.value)
    assert "do-not-print-this" not in str(error.value)


def test_rejects_duplicate_names_case_insensitively():
    with pytest.raises(SiteWatchError, match="names must be unique"):
        config_from_dict(
            {"schema_version": 1, "targets": [target("API"), target("api")]}
        )


def test_load_config_reports_invalid_json_without_content(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("secret invalid material", encoding="utf-8")

    with pytest.raises(SiteWatchError) as error:
        load_config(path)

    assert "not valid JSON" in str(error.value)
    assert "secret invalid material" not in str(error.value)
