"""Privacy-safe reports for local reliability policy decisions."""

from __future__ import annotations

import json
from typing import Any

from .reliability import AlertDecision


def alert_decision_to_dict(decision: AlertDecision) -> dict[str, Any]:
    """Return aggregate checks without targets or observation details."""

    return {
        "alert": decision.alert,
        "policy": decision.policy_name,
        "summary": {
            "targets": decision.targets,
            "samples": decision.samples,
            "checks": len(decision.checks),
            "failed_checks": decision.failed_checks,
        },
        "finding_codes": list(decision.finding_codes),
        "checks": [
            {
                "code": check.code,
                "observed": check.observed,
                "limit": check.limit,
                "passed": check.passed,
            }
            for check in decision.checks
        ],
    }


def format_alert_decision(
    decision: AlertDecision,
    *,
    as_json: bool = False,
) -> str:
    """Format a deterministic decision for people or automation."""

    payload = alert_decision_to_dict(decision)
    if as_json:
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    lines = [
        "SiteWatch reliability decision",
        f"Policy: {decision.policy_name}",
        f"Decision: {'alert' if decision.alert else 'clear'}",
        f"Targets: {decision.targets}",
        f"Samples: {decision.samples}",
        f"Failed checks: {decision.failed_checks}",
        "",
        "Checks",
    ]
    for check in payload["checks"]:
        lines.append(
            f"- {check['code']}: {'passed' if check['passed'] else 'failed'} "
            f"(observed {check['observed']:g}, limit {check['limit']:g})"
        )
    return "\n".join(lines).rstrip() + "\n"
