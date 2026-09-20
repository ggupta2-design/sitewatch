"""Strict local reliability policies for SiteWatch history."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .incidents import MAXIMUM_GAP_SECONDS
from .safety import SiteWatchError

_ROOT_FIELDS = {
    "schema_version",
    "name",
    "minimum_availability",
    "maximum_open_incidents",
    "maximum_monitoring_gaps",
    "maximum_errors",
    "maximum_gap_seconds",
}
MAXIMUM_POLICY_COUNT = 10_000


def _text(value: Any, field: str, *, maximum: int = 100) -> str:
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


def _bounded_count(value: Any, field: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= MAXIMUM_POLICY_COUNT
    ):
        raise SiteWatchError(
            f"{field} must be from 0 to {MAXIMUM_POLICY_COUNT}"
        )
    return value


@dataclass(frozen=True)
class ReliabilityPolicy:
    """Named thresholds for a local history review."""

    name: str
    minimum_availability: float
    maximum_open_incidents: int
    maximum_monitoring_gaps: int
    maximum_errors: int
    maximum_gap_seconds: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "policy name"))
        if (
            isinstance(self.minimum_availability, bool)
            or not isinstance(self.minimum_availability, (int, float))
            or not 0 <= self.minimum_availability <= 100
        ):
            raise SiteWatchError("minimum_availability must be from 0 to 100")
        object.__setattr__(
            self, "minimum_availability", float(self.minimum_availability)
        )
        for field in (
            "maximum_open_incidents",
            "maximum_monitoring_gaps",
            "maximum_errors",
        ):
            object.__setattr__(
                self, field, _bounded_count(getattr(self, field), field)
            )
        if (
            isinstance(self.maximum_gap_seconds, bool)
            or not isinstance(self.maximum_gap_seconds, int)
            or not 1 <= self.maximum_gap_seconds <= MAXIMUM_GAP_SECONDS
        ):
            raise SiteWatchError(
                f"maximum_gap_seconds must be from 1 to {MAXIMUM_GAP_SECONDS}"
            )


def policy_from_dict(payload: Any) -> ReliabilityPolicy:
    if not isinstance(payload, dict) or set(payload) != _ROOT_FIELDS:
        raise SiteWatchError(
            "reliability policy must contain exactly the supported fields"
        )
    if payload["schema_version"] != 1:
        raise SiteWatchError(
            f"unsupported reliability policy schema_version: "
            f"{payload['schema_version']}"
        )
    values = dict(payload)
    values.pop("schema_version")
    return ReliabilityPolicy(**values)


def policy_to_dict(policy: ReliabilityPolicy) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": policy.name,
        "minimum_availability": policy.minimum_availability,
        "maximum_open_incidents": policy.maximum_open_incidents,
        "maximum_monitoring_gaps": policy.maximum_monitoring_gaps,
        "maximum_errors": policy.maximum_errors,
        "maximum_gap_seconds": policy.maximum_gap_seconds,
    }


def format_policy(policy: ReliabilityPolicy) -> str:
    return json.dumps(policy_to_dict(policy), indent=2, sort_keys=True) + "\n"


def load_policy(path: str | Path) -> ReliabilityPolicy:
    """Load a strict UTF-8 policy without exposing file contents in errors."""

    source = Path(path)
    if not source.exists():
        raise SiteWatchError("reliability policy file does not exist")
    if not source.is_file():
        raise SiteWatchError("reliability policy path is not a file")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise SiteWatchError("reliability policy is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise SiteWatchError(
            f"reliability policy is not valid JSON at line {exc.lineno}"
        ) from exc
    except OSError as exc:
        raise SiteWatchError("could not read reliability policy") from exc
    return policy_from_dict(payload)
