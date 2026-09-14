"""Deterministic evaluation of SiteWatch observations."""

from __future__ import annotations

from dataclasses import dataclass

from .http import observe_target
from .models import CheckResult, CheckState, Observation, Target


def evaluate_observation(target: Target, observation: Observation) -> CheckResult:
    """Evaluate response metadata using stable, non-content findings."""

    findings: list[str] = []
    if observation.error_code:
        findings.append(observation.error_code)
        state = CheckState.ERROR
    else:
        if observation.status not in target.expected_statuses:
            findings.append("unexpected_status")
        if (
            not target.allow_redirects
            and observation.final_url is not None
            and observation.final_url != target.url
        ):
            findings.append("unexpected_redirect")
        if target.expected_content_type is not None:
            actual = (observation.content_type or "").casefold()
            if actual != target.expected_content_type:
                findings.append("unexpected_content_type")
        state = CheckState.HEALTHY if not findings else CheckState.UNHEALTHY

    return CheckResult(
        name=target.name,
        configured_url=target.url,
        state=state,
        observation=observation,
        findings=tuple(sorted(findings)),
    )


@dataclass(frozen=True)
class CheckRun:
    """Ordered results for one configuration run."""

    results: tuple[CheckResult, ...]

    @property
    def healthy(self) -> bool:
        return bool(self.results) and all(item.healthy for item in self.results)

    @property
    def healthy_count(self) -> int:
        return sum(item.healthy for item in self.results)

    @property
    def unhealthy_count(self) -> int:
        return len(self.results) - self.healthy_count


def run_checks(targets: tuple[Target, ...], *, observer=observe_target) -> CheckRun:
    """Check targets sequentially to keep network activity predictable."""

    return CheckRun(
        tuple(
            evaluate_observation(target, observer(target))
            for target in targets
        )
    )
