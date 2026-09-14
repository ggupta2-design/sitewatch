"""Validated models for SiteWatch checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .safety import SiteWatchError, validate_http_url


def _text(value: str, field: str, *, maximum: int = 200) -> str:
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
class Target:
    """One bounded website health-check target."""

    name: str
    url: str
    expected_statuses: tuple[int, ...] = (200,)
    timeout_seconds: float = 10.0
    max_bytes: int = 1_000_000
    expected_content_type: str | None = None
    allow_redirects: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "target name"))
        object.__setattr__(self, "url", validate_http_url(self.url))
        statuses = self.expected_statuses
        if (
            not isinstance(statuses, tuple)
            or not 1 <= len(statuses) <= 10
            or any(
                isinstance(item, bool)
                or not isinstance(item, int)
                or not 100 <= item <= 599
                for item in statuses
            )
        ):
            raise SiteWatchError(
                "expected_statuses must contain 1 to 10 HTTP status integers"
            )
        object.__setattr__(self, "expected_statuses", tuple(sorted(set(statuses))))
        timeout = self.timeout_seconds
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not 0.1 <= timeout <= 60
        ):
            raise SiteWatchError("timeout_seconds must be from 0.1 to 60")
        object.__setattr__(self, "timeout_seconds", float(timeout))
        if (
            isinstance(self.max_bytes, bool)
            or not isinstance(self.max_bytes, int)
            or not 1 <= self.max_bytes <= 10_000_000
        ):
            raise SiteWatchError("max_bytes must be from 1 to 10000000")
        if self.expected_content_type is not None:
            object.__setattr__(
                self,
                "expected_content_type",
                _text(
                    self.expected_content_type,
                    "expected_content_type",
                    maximum=200,
                ).casefold(),
            )
        if not isinstance(self.allow_redirects, bool):
            raise SiteWatchError("allow_redirects must be true or false")


class CheckState(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    ERROR = "error"


@dataclass(frozen=True)
class Observation:
    """Bounded response metadata; response bodies are never retained."""

    status: int | None
    final_url: str | None
    duration_ms: int
    content_type: str | None
    bytes_read: int
    sha256: str | None
    checked_at: datetime
    error_code: str | None = None


@dataclass(frozen=True)
class CheckResult:
    """Evaluated outcome for one target."""

    name: str
    configured_url: str
    state: CheckState
    observation: Observation
    findings: tuple[str, ...] = ()

    @property
    def healthy(self) -> bool:
        return self.state is CheckState.HEALTHY
