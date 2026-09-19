"""Read-only incident, recovery, and observation-gap analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .history import AvailabilityHistory, HistorySample
from .models import CheckState
from .safety import SiteWatchError

MAXIMUM_GAP_SECONDS = 31_536_000


@dataclass(frozen=True)
class IncidentRecord:
    """One consecutive sequence of observed non-healthy samples."""

    name: str
    started_at: datetime
    last_failure_at: datetime
    recovered_at: datetime | None
    samples: int
    unhealthy_samples: int
    error_samples: int
    maximum_duration_ms: int

    @property
    def open(self) -> bool:
        return self.recovered_at is None

    @property
    def observed_seconds(self) -> int:
        end = self.recovered_at or self.last_failure_at
        return int((end - self.started_at).total_seconds())


@dataclass(frozen=True)
class MonitoringGap:
    """An interval between samples that exceeds the selected bound."""

    name: str
    previous_checked_at: datetime
    next_checked_at: datetime
    seconds: int


@dataclass(frozen=True)
class IncidentAnalysis:
    """Deterministic incident and monitoring-gap records."""

    incidents: tuple[IncidentRecord, ...]
    gaps: tuple[MonitoringGap, ...]
    maximum_gap_seconds: int

    @property
    def incident_count(self) -> int:
        return len(self.incidents)

    @property
    def recovered_count(self) -> int:
        return sum(not incident.open for incident in self.incidents)

    @property
    def open_count(self) -> int:
        return sum(incident.open for incident in self.incidents)

    @property
    def gap_count(self) -> int:
        return len(self.gaps)

    @property
    def affected_samples(self) -> int:
        return sum(incident.samples for incident in self.incidents)

    @property
    def unhealthy_samples(self) -> int:
        return sum(incident.unhealthy_samples for incident in self.incidents)

    @property
    def error_samples(self) -> int:
        return sum(incident.error_samples for incident in self.incidents)

    @property
    def attention_required(self) -> bool:
        return self.open_count > 0 or self.gap_count > 0

    @property
    def healthy(self) -> bool:
        return not self.attention_required


def _record(name: str, failures: list[HistorySample], recovered_at: datetime | None) -> IncidentRecord:
    return IncidentRecord(
        name=name,
        started_at=failures[0].checked_at,
        last_failure_at=failures[-1].checked_at,
        recovered_at=recovered_at,
        samples=len(failures),
        unhealthy_samples=sum(
            sample.state is CheckState.UNHEALTHY for sample in failures
        ),
        error_samples=sum(sample.state is CheckState.ERROR for sample in failures),
        maximum_duration_ms=max(sample.duration_ms for sample in failures),
    )


def analyze_incidents(
    history: AvailabilityHistory,
    *,
    maximum_gap_seconds: int = 3_600,
) -> IncidentAnalysis:
    """Group failures and flag intervals that exceed the observation bound."""

    if (
        isinstance(maximum_gap_seconds, bool)
        or not isinstance(maximum_gap_seconds, int)
        or not 1 <= maximum_gap_seconds <= MAXIMUM_GAP_SECONDS
    ):
        raise SiteWatchError(
            f"maximum_gap_seconds must be from 1 to {MAXIMUM_GAP_SECONDS}"
        )

    grouped: dict[str, list[HistorySample]] = {}
    names: dict[str, str] = {}
    for sample in history.samples:
        key = sample.name.casefold()
        grouped.setdefault(key, []).append(sample)
        names.setdefault(key, sample.name)

    incidents: list[IncidentRecord] = []
    gaps: list[MonitoringGap] = []
    for key in sorted(grouped):
        samples = grouped[key]
        for previous, current in zip(samples, samples[1:]):
            seconds = int((current.checked_at - previous.checked_at).total_seconds())
            if seconds > maximum_gap_seconds:
                gaps.append(
                    MonitoringGap(
                        name=names[key],
                        previous_checked_at=previous.checked_at,
                        next_checked_at=current.checked_at,
                        seconds=seconds,
                    )
                )

        failures: list[HistorySample] = []
        for sample in samples:
            if sample.state is CheckState.HEALTHY:
                if failures:
                    incidents.append(_record(names[key], failures, sample.checked_at))
                    failures = []
            else:
                failures.append(sample)
        if failures:
            incidents.append(_record(names[key], failures, None))

    return IncidentAnalysis(
        incidents=tuple(
            sorted(incidents, key=lambda item: (item.started_at, item.name.casefold()))
        ),
        gaps=tuple(
            sorted(
                gaps,
                key=lambda item: (item.previous_checked_at, item.name.casefold()),
            )
        ),
        maximum_gap_seconds=maximum_gap_seconds,
    )
