import pytest

from sitewatch.output import write_output
from sitewatch.safety import SiteWatchError


def test_writes_new_output_and_creates_parent(tmp_path):
    destination = tmp_path / "reports" / "health.json"

    result = write_output(destination, '{"healthy": true}\n')

    assert result == destination
    assert destination.read_text(encoding="utf-8") == '{"healthy": true}\n'
    assert not list(destination.parent.glob(".*.tmp"))


def test_refuses_to_replace_existing_output(tmp_path):
    destination = tmp_path / "health.txt"
    destination.write_text("preserve", encoding="utf-8")

    with pytest.raises(SiteWatchError, match="already exists"):
        write_output(destination, "replacement")

    assert destination.read_text(encoding="utf-8") == "preserve"


def test_does_not_leave_temporary_file_after_link_failure(tmp_path, monkeypatch):
    destination = tmp_path / "health.txt"

    def fail_link(source, target):
        raise OSError("simulated")

    monkeypatch.setattr("sitewatch.output.os.link", fail_link)

    with pytest.raises(SiteWatchError, match="could not write output"):
        write_output(destination, "content")

    assert not destination.exists()
    assert not list(tmp_path.glob(".*.tmp"))
