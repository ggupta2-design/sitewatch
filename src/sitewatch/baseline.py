"""Strict, body-free SiteWatch baseline snapshots."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .checks import CheckRun
from .models import CheckState
from .safety import SiteWatchError, validate_http_url

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ROOT_FIELDS = {"schema_version", "targets"}
_ENTRY_FIELDS = {"name", "configured_url", "state", "status", "content_type", "sha256"}


def _clean_text(value: Any, field: str, *, maximum: int = 200) -> str:
    if not isinstance(value, str):
        raise SiteWatchError(f"{field} must be text")
    cleaned = value.strip()
    if not cleaned:
        raise SiteWatchError(f"{field} cannot be blank")
    if len(cleaned) > maximum:
        raise SiteWatchError(f"{field} cannot exceed {maximum} characters")
    if any(ord(character) < 32 for character in cleaned):
        raise SiteWatchError(f"{field} cannot contain control characters")
    return cleaned


@dataclass(frozen=True)
class BaselineEntry:
    """Stable metadata for one checked target; response bodies are excluded."""

    name: str
    configured_url: str
    state: CheckState
    status: int | None
    content_type: str | None
    sha256: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _clean_text(self.name, "baseline name"))
        object.__setattr__(
            self, "configured_url", validate_http_url(self.configured_url)
        )
        if isinstance(self.state, str):
            try:
                object.__setattr__(self, "state", CheckState(self.state))
            except ValueError as exc:
                raise SiteWatchError("baseline state is not supported") from exc
        if not isinstance(self.state, CheckState):
            raise SiteWatchError("baseline state is not supported")
        if self.status is not None and (
            isinstance(self.status, bool)
            or not isinstance(self.status, int)
            or not 100 <= self.status <= 599
        ):
            raise SiteWatchError("baseline status must be null or an HTTP status")
        if self.content_type is not None:
            object.__setattr__(
                self,
                "content_type",
                _clean_text(
                    self.content_type, "baseline content_type", maximum=200
                ).casefold(),
            )
        if self.sha256 is not None and (
            not isinstance(self.sha256, str) or not _SHA256.fullmatch(self.sha256)
        ):
            raise SiteWatchError(
                "baseline sha256 must be null or a lowercase SHA-256 digest"
            )


@dataclass(frozen=True)
class Baseline:
    """A bounded, uniquely named collection of baseline entries."""

    entries: tuple[BaselineEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple) or not 1 <= len(self.entries) <= 100:
            raise SiteWatchError("baseline targets must contain from 1 to 100 entries")
        if any(not isinstance(entry, BaselineEntry) for entry in self.entries):
            raise SiteWatchError("baseline targets must be valid entries")
        names = [entry.name.casefold() for entry in self.entries]
        if len(names) != len(set(names)):
            raise SiteWatchError("baseline target names must be unique")


def baseline_from_run(run: CheckRun) -> Baseline:
    """Capture only stable response metadata from a completed check run."""

    return Baseline(
        tuple(
            BaselineEntry(
                name=result.name,
                configured_url=result.configured_url,
                state=result.state,
                status=result.observation.status,
                content_type=result.observation.content_type,
                sha256=result.observation.sha256,
            )
            for result in run.results
        )
    )


def baseline_to_dict(baseline: Baseline) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "targets": [
            {
                "name": entry.name,
                "configured_url": entry.configured_url,
                "state": entry.state.value,
                "status": entry.status,
                "content_type": entry.content_type,
                "sha256": entry.sha256,
            }
            for entry in baseline.entries
        ],
    }


def format_baseline(baseline: Baseline) -> str:
    """Serialize a baseline deterministically for safe local storage."""

    return json.dumps(baseline_to_dict(baseline), indent=2, sort_keys=True) + "\n"


def baseline_from_dict(payload: Any) -> Baseline:
    if not isinstance(payload, dict) or set(payload) != _ROOT_FIELDS:
        raise SiteWatchError("baseline must contain exactly the supported fields")
    if payload["schema_version"] != 1:
        raise SiteWatchError(
            f"unsupported baseline schema_version: {payload['schema_version']}"
        )
    targets = payload["targets"]
    if not isinstance(targets, list):
        raise SiteWatchError("baseline targets must be a list")
    entries = []
    for index, item in enumerate(targets):
        if not isinstance(item, dict) or set(item) != _ENTRY_FIELDS:
            raise SiteWatchError(
                f"baseline targets[{index}] must contain exactly the supported fields"
            )
        entries.append(BaselineEntry(**item))
    return Baseline(tuple(entries))


def load_baseline(path: str | Path) -> Baseline:
    """Load one strict UTF-8 baseline without exposing its contents in errors."""

    source = Path(path)
    if not source.exists():
        raise SiteWatchError("baseline file does not exist")
    if not source.is_file():
        raise SiteWatchError("baseline path is not a file")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise SiteWatchError("baseline is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise SiteWatchError(
            f"baseline is not valid JSON at line {exc.lineno}"
        ) from exc
    except OSError as exc:
        raise SiteWatchError("could not read baseline") from exc
    return baseline_from_dict(payload)
