"""Policy-based, notification-ready decisions for SiteWatch history."""

from __future__ import annotations

from dataclasses import dataclass

from .availability import summarize_availability
from .history import AvailabilityHistory
from .incidents import analyze_incidents
from .reliability_policy import ReliabilityPolicy


@dataclass(frozen=True)
class ReliabilityCheck:
    """One stable policy comparison containing aggregate values only."""

    code: str
    observed: int | float
    limit: int | float
    passed: bool


@dataclass(frozen=True)
class AlertDecision:
    """Deterministic local decision suitable for downstream automation."""

    policy_name: str
    checks: tuple[ReliabilityCheck, ...]
    samples: int
    targets: int

    @property
    def alert(self) -> bool:
        return any(not check.passed for check in self.checks)

    @property
    def finding_codes(self) -> tuple[str, ...]:
        return tuple(check.code for check in self.checks if not check.passed)

    @property
    def failed_checks(self) -> int:
        return len(self.finding_codes)


def evaluate_reliability(
    history: AvailabilityHistory,
    policy: ReliabilityPolicy,
) -> AlertDecision:
    """Evaluate aggregate history evidence against a strict local policy."""

    availability = summarize_availability(
        history,
        minimum_availability=policy.minimum_availability,
    )
    incidents = analyze_incidents(
        history,
        maximum_gap_seconds=policy.maximum_gap_seconds,
    )
    lowest_availability = min(
        target.availability_percent for target in availability.targets
    )
    checks = (
        ReliabilityCheck(
            code="availability_below_minimum",
            observed=lowest_availability,
            limit=policy.minimum_availability,
            passed=lowest_availability >= policy.minimum_availability,
        ),
        ReliabilityCheck(
            code="open_incidents_exceeded",
            observed=incidents.open_count,
            limit=policy.maximum_open_incidents,
            passed=incidents.open_count <= policy.maximum_open_incidents,
        ),
        ReliabilityCheck(
            code="monitoring_gaps_exceeded",
            observed=incidents.gap_count,
            limit=policy.maximum_monitoring_gaps,
            passed=incidents.gap_count <= policy.maximum_monitoring_gaps,
        ),
        ReliabilityCheck(
            code="errors_exceeded",
            observed=availability.errors,
            limit=policy.maximum_errors,
            passed=availability.errors <= policy.maximum_errors,
        ),
    )
    return AlertDecision(
        policy_name=policy.name,
        checks=checks,
        samples=availability.samples,
        targets=len(availability.targets),
    )
