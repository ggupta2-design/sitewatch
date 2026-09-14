from dataclasses import FrozenInstanceError

import pytest

from sitewatch.models import Target
from sitewatch.safety import SiteWatchError


def test_target_normalizes_and_sorts_expectations():
    target = Target(
        name="  Homepage ",
        url="HTTPS://Example.COM",
        expected_statuses=(204, 200, 200),
        timeout_seconds=2,
        max_bytes=4096,
        expected_content_type=" Text/HTML ",
        allow_redirects=True,
    )

    assert target.name == "Homepage"
    assert target.url == "https://example.com/"
    assert target.expected_statuses == (200, 204)
    assert target.timeout_seconds == 2.0
    assert target.expected_content_type == "text/html"
    with pytest.raises(FrozenInstanceError):
        target.name = "changed"


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"name": ""}, "target name"),
        ({"expected_statuses": ()}, "expected_statuses"),
        ({"expected_statuses": (99,)}, "expected_statuses"),
        ({"expected_statuses": (True,)}, "expected_statuses"),
        ({"timeout_seconds": 0}, "timeout_seconds"),
        ({"timeout_seconds": 61}, "timeout_seconds"),
        ({"max_bytes": 0}, "max_bytes"),
        ({"max_bytes": 10_000_001}, "max_bytes"),
        ({"expected_content_type": ""}, "expected_content_type"),
        ({"allow_redirects": 1}, "allow_redirects"),
    ],
)
def test_rejects_invalid_target_bounds(changes, message):
    values = {
        "name": "Homepage",
        "url": "https://example.com/",
        "expected_statuses": (200,),
        "timeout_seconds": 10,
        "max_bytes": 1000,
        "expected_content_type": None,
        "allow_redirects": False,
    }
    values.update(changes)

    with pytest.raises(SiteWatchError, match=message):
        Target(**values)
