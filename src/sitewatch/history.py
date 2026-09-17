"""Strict, bounded availability history for SiteWatch."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .checks import CheckRun
from .models import CheckState
from .safety import SiteWatchError

_ROOT_FIELDS = {"schema_version", "samples"}
_SAMPLE_FIELDS = {
    "name",
    "checked_at",
    "state",
    "status",
    "duration_ms",
    "error_code",
}
MAX_HISTORY_SAMPLES = 10_000


def _text(value: Any, field: str, *, maximum: int = 200) -> str:
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


def _utc_datetime(value: Any) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise SiteWatchError("history checked_at must include a timezone")
    return value.astimezone(timezone.utc)


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise SiteWatchError("history checked_at must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SiteWatchError("history checked_at must be an ISO timestamp") from exc
    return _utc_datetime(parsed)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class HistorySample:
    """One value-limited target observation for availability analysis."""

    name: str
    checked_at: datetime
    state: CheckState
    status: int | None
    duration_ms: int
    error_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "history name"))
        object.__setattr__(self, "checked_at", _utc_datetime(self.checked_at))
        if isinstance(self.state, str):
            try:
                object.__setattr__(self, "state", CheckState(self.state))
            except ValueError as exc:
                raise SiteWatchError("history state is not supported") from exc
        if not isinstance(self.state, CheckState):
            raise SiteWatchError("history state is not supported")
        if self.status is not None and (
            isinstance(self.status, bool)
            or not isinstance(self.status, int)
            or not 100 <= self.status <= 599
        ):
            raise SiteWatchError("history status must be null or an HTTP status")
        if (
            isinstance(self.duration_ms, bool)
            or not isinstance(self.duration_ms, int)
            or not 0 <= self.duration_ms <= 3_600_000
        ):
            raise SiteWatchError("history duration_ms must be from 0 to 3600000")
        if self.error_code is not None:
            object.__setattr__(
                self,
                "error_code",
                _text(self.error_code, "history error_code", maximum=100),
            )


@dataclass(frozen=True)
class AvailabilityHistory:
    """Chronological, duplicate-free samples with a hard size bound."""

    samples: tuple[HistorySample, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.samples, tuple)
            or not 1 <= len(self.samples) <= MAX_HISTORY_SAMPLES
        ):
            raise SiteWatchError(
                f"history samples must contain from 1 to {MAX_HISTORY_SAMPLES} entries"
            )
        if any(not isinstance(sample, HistorySample) for sample in self.samples):
            raise SiteWatchError("history samples must be valid entries")
        ordered = tuple(
            sorted(
                self.samples,
                key=lambda item: (item.checked_at, item.name.casefold()),
            )
        )
        object.__setattr__(self, "samples", ordered)
        keys = [
            (sample.name.casefold(), sample.checked_at)
            for sample in ordered
        ]
        if len(keys) != len(set(keys)):
            raise SiteWatchError("history samples must be unique by name and time")

    @property
    def first_checked_at(self) -> datetime:
        return self.samples[0].checked_at

    @property
    def last_checked_at(self) -> datetime:
        return self.samples[-1].checked_at


def history_from_run(run: CheckRun) -> AvailabilityHistory:
    """Capture state, status, latency, and stable error codes only."""

    return AvailabilityHistory(
        tuple(
            HistorySample(
                name=result.name,
                checked_at=result.observation.checked_at,
                state=result.state,
                status=result.observation.status,
                duration_ms=result.observation.duration_ms,
                error_code=result.observation.error_code,
            )
            for result in run.results
        )
    )


def append_history(
    history: AvailabilityHistory,
    run: CheckRun,
) -> AvailabilityHistory:
    """Return a new immutable history containing a strictly later check run."""

    addition = history_from_run(run)
    if addition.first_checked_at <= history.last_checked_at:
        raise SiteWatchError("new history samples must be later than existing samples")
    return AvailabilityHistory(history.samples + addition.samples)


def history_to_dict(history: AvailabilityHistory) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "samples": [
            {
                "name": sample.name,
                "checked_at": _format_timestamp(sample.checked_at),
                "state": sample.state.value,
                "status": sample.status,
                "duration_ms": sample.duration_ms,
                "error_code": sample.error_code,
            }
            for sample in history.samples
        ],
    }


def format_history(history: AvailabilityHistory) -> str:
    return json.dumps(history_to_dict(history), indent=2, sort_keys=True) + "\n"


def history_from_dict(payload: Any) -> AvailabilityHistory:
    if not isinstance(payload, dict) or set(payload) != _ROOT_FIELDS:
        raise SiteWatchError("history must contain exactly the supported fields")
    if payload["schema_version"] != 1:
        raise SiteWatchError(
            f"unsupported history schema_version: {payload['schema_version']}"
        )
    raw_samples = payload["samples"]
    if not isinstance(raw_samples, list):
        raise SiteWatchError("history samples must be a list")
    samples = []
    for index, item in enumerate(raw_samples):
        if not isinstance(item, dict) or set(item) != _SAMPLE_FIELDS:
            raise SiteWatchError(
                f"history samples[{index}] must contain exactly the supported fields"
            )
        values = dict(item)
        values["checked_at"] = _parse_timestamp(values["checked_at"])
        samples.append(HistorySample(**values))
    return AvailabilityHistory(tuple(samples))


def load_history(path: str | Path) -> AvailabilityHistory:
    """Load strict UTF-8 history without exposing file contents in errors."""

    source = Path(path)
    if not source.exists():
        raise SiteWatchError("history file does not exist")
    if not source.is_file():
        raise SiteWatchError("history path is not a file")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise SiteWatchError("history is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise SiteWatchError(
            f"history is not valid JSON at line {exc.lineno}"
        ) from exc
    except OSError as exc:
        raise SiteWatchError("could not read history") from exc
    return history_from_dict(payload)
