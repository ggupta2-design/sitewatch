"""Read-only incident and recovery analysis for SiteWatch history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .history import AvailabilityHistory, HistorySample
from .models import CheckState


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
class IncidentAnalysis:
    """Deterministic incident records across a bounded history."""

    incidents: tuple[IncidentRecord, ...]

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
    def affected_samples(self) -> int:
        return sum(incident.samples for incident in self.incidents)

    @property
    def unhealthy_samples(self) -> int:
        return sum(incident.unhealthy_samples for incident in self.incidents)

    @property
    def error_samples(self) -> int:
        return sum(incident.error_samples for incident in self.incidents)

    @property
    def healthy(self) -> bool:
        return self.open_count == 0


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


def analyze_incidents(history: AvailabilityHistory) -> IncidentAnalysis:
    """Group consecutive non-healthy observations by target name."""

    grouped: dict[str, list[HistorySample]] = {}
    names: dict[str, str] = {}
    for sample in history.samples:
        key = sample.name.casefold()
        grouped.setdefault(key, []).append(sample)
        names.setdefault(key, sample.name)

    incidents: list[IncidentRecord] = []
    for key in sorted(grouped):
        failures: list[HistorySample] = []
        for sample in grouped[key]:
            if sample.state is CheckState.HEALTHY:
                if failures:
                    incidents.append(_record(names[key], failures, sample.checked_at))
                    failures = []
            else:
                failures.append(sample)
        if failures:
            incidents.append(_record(names[key], failures, None))

    return IncidentAnalysis(
        tuple(sorted(incidents, key=lambda item: (item.started_at, item.name.casefold())))
    )
