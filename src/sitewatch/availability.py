"""Aggregate reliability summaries for SiteWatch history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .history import AvailabilityHistory, HistorySample
from .models import CheckState
from .safety import SiteWatchError


@dataclass(frozen=True)
class TargetAvailability:
    """Count-only reliability and latency metrics for one target name."""

    name: str
    samples: int
    healthy: int
    unhealthy: int
    errors: int
    availability_percent: float
    average_duration_ms: int
    maximum_duration_ms: int
    first_checked_at: datetime
    last_checked_at: datetime
    meets_goal: bool


@dataclass(frozen=True)
class AvailabilitySummary:
    """Deterministic metrics across a bounded history."""

    targets: tuple[TargetAvailability, ...]
    minimum_availability: float

    @property
    def samples(self) -> int:
        return sum(target.samples for target in self.targets)

    @property
    def healthy(self) -> int:
        return sum(target.healthy for target in self.targets)

    @property
    def unhealthy(self) -> int:
        return sum(target.unhealthy for target in self.targets)

    @property
    def errors(self) -> int:
        return sum(target.errors for target in self.targets)

    @property
    def availability_percent(self) -> float:
        return round((self.healthy / self.samples) * 100, 3)

    @property
    def meets_goal(self) -> bool:
        return all(target.meets_goal for target in self.targets)

    @property
    def below_goal_count(self) -> int:
        return sum(not target.meets_goal for target in self.targets)


def _target_summary(
    name: str,
    samples: list[HistorySample],
    *,
    minimum_availability: float,
) -> TargetAvailability:
    healthy = sum(item.state is CheckState.HEALTHY for item in samples)
    unhealthy = sum(item.state is CheckState.UNHEALTHY for item in samples)
    errors = sum(item.state is CheckState.ERROR for item in samples)
    percent = round((healthy / len(samples)) * 100, 3)
    durations = [item.duration_ms for item in samples]
    return TargetAvailability(
        name=name,
        samples=len(samples),
        healthy=healthy,
        unhealthy=unhealthy,
        errors=errors,
        availability_percent=percent,
        average_duration_ms=round(sum(durations) / len(durations)),
        maximum_duration_ms=max(durations),
        first_checked_at=min(item.checked_at for item in samples),
        last_checked_at=max(item.checked_at for item in samples),
        meets_goal=percent >= minimum_availability,
    )


def summarize_availability(
    history: AvailabilityHistory,
    *,
    minimum_availability: float = 99.0,
) -> AvailabilitySummary:
    """Summarize each target without URLs or observation content."""

    if (
        isinstance(minimum_availability, bool)
        or not isinstance(minimum_availability, (int, float))
        or not 0 <= minimum_availability <= 100
    ):
        raise SiteWatchError("minimum_availability must be from 0 to 100")
    goal = float(minimum_availability)
    grouped: dict[str, list[HistorySample]] = {}
    names: dict[str, str] = {}
    for sample in history.samples:
        key = sample.name.casefold()
        grouped.setdefault(key, []).append(sample)
        names.setdefault(key, sample.name)

    targets = tuple(
        _target_summary(
            names[key],
            grouped[key],
            minimum_availability=goal,
        )
        for key in sorted(grouped)
    )
    return AvailabilitySummary(targets, minimum_availability=goal)
