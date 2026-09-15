"""Deterministic comparisons between SiteWatch runs and baselines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .baseline import Baseline, BaselineEntry, baseline_from_run
from .checks import CheckRun


class DriftState(str, Enum):
    UNCHANGED = "unchanged"
    CHANGED = "changed"
    NEW = "new"
    MISSING = "missing"


@dataclass(frozen=True)
class DriftResult:
    """Value-free comparison outcome for one named target."""

    name: str
    state: DriftState
    changed_fields: tuple[str, ...]
    configured_url: str | None

    @property
    def drifted(self) -> bool:
        return self.state is not DriftState.UNCHANGED


@dataclass(frozen=True)
class DriftRun:
    """Ordered change results for one current run."""

    results: tuple[DriftResult, ...]
    current_healthy: bool

    @property
    def has_drift(self) -> bool:
        return any(item.drifted for item in self.results)

    @property
    def unchanged_count(self) -> int:
        return sum(item.state is DriftState.UNCHANGED for item in self.results)

    @property
    def changed_count(self) -> int:
        return sum(item.state is DriftState.CHANGED for item in self.results)

    @property
    def new_count(self) -> int:
        return sum(item.state is DriftState.NEW for item in self.results)

    @property
    def missing_count(self) -> int:
        return sum(item.state is DriftState.MISSING for item in self.results)


def _changed_fields(before: BaselineEntry, after: BaselineEntry) -> tuple[str, ...]:
    fields = (
        "configured_url",
        "state",
        "status",
        "content_type",
        "sha256",
    )
    return tuple(
        field for field in fields
        if getattr(before, field) != getattr(after, field)
    )


def compare_to_baseline(current: CheckRun, baseline: Baseline) -> DriftRun:
    """Compare by case-insensitive unique names without disclosing values."""

    current_snapshot = baseline_from_run(current)
    previous_by_name = {
        entry.name.casefold(): entry for entry in baseline.entries
    }
    current_names: set[str] = set()
    results: list[DriftResult] = []

    for entry in current_snapshot.entries:
        key = entry.name.casefold()
        current_names.add(key)
        previous = previous_by_name.get(key)
        if previous is None:
            results.append(
                DriftResult(
                    name=entry.name,
                    state=DriftState.NEW,
                    changed_fields=("target",),
                    configured_url=entry.configured_url,
                )
            )
            continue
        changes = _changed_fields(previous, entry)
        results.append(
            DriftResult(
                name=entry.name,
                state=DriftState.CHANGED if changes else DriftState.UNCHANGED,
                changed_fields=changes,
                configured_url=entry.configured_url,
            )
        )

    for entry in baseline.entries:
        if entry.name.casefold() not in current_names:
            results.append(
                DriftResult(
                    name=entry.name,
                    state=DriftState.MISSING,
                    changed_fields=("target",),
                    configured_url=entry.configured_url,
                )
            )

    return DriftRun(tuple(results), current_healthy=current.healthy)
