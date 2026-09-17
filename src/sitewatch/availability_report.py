"""Privacy-first availability history reports."""

from __future__ import annotations

import json
from typing import Any

from .availability import AvailabilitySummary


def _timestamp(value) -> str:
    return value.isoformat().replace("+00:00", "Z")


def availability_summary_to_dict(
    summary: AvailabilitySummary,
) -> dict[str, Any]:
    """Return count-only reliability metrics without URLs or fingerprints."""

    return {
        "meets_goal": summary.meets_goal,
        "minimum_availability": summary.minimum_availability,
        "summary": {
            "targets": len(summary.targets),
            "samples": summary.samples,
            "healthy": summary.healthy,
            "unhealthy": summary.unhealthy,
            "errors": summary.errors,
            "availability_percent": summary.availability_percent,
            "below_goal": summary.below_goal_count,
        },
        "targets": [
            {
                "name": target.name,
                "samples": target.samples,
                "healthy": target.healthy,
                "unhealthy": target.unhealthy,
                "errors": target.errors,
                "availability_percent": target.availability_percent,
                "average_duration_ms": target.average_duration_ms,
                "maximum_duration_ms": target.maximum_duration_ms,
                "first_checked_at": _timestamp(target.first_checked_at),
                "last_checked_at": _timestamp(target.last_checked_at),
                "meets_goal": target.meets_goal,
            }
            for target in summary.targets
        ],
    }


def format_availability_summary(
    summary: AvailabilitySummary,
    *,
    as_json: bool = False,
) -> str:
    """Format an availability summary for people or automation."""

    payload = availability_summary_to_dict(summary)
    if as_json:
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    totals = payload["summary"]
    lines = [
        "SiteWatch availability summary",
        f"Goal: {summary.minimum_availability:g}%",
        f"Status: {'met' if summary.meets_goal else 'below goal'}",
        f"Targets: {totals['targets']}",
        f"Samples: {totals['samples']}",
        f"Healthy: {totals['healthy']}",
        f"Unhealthy: {totals['unhealthy']}",
        f"Errors: {totals['errors']}",
        f"Availability: {totals['availability_percent']:g}%",
        f"Below goal: {totals['below_goal']}",
        "",
    ]
    for target in payload["targets"]:
        lines.append(
            f"{target['name']}: {target['availability_percent']:g}% "
            f"({'met' if target['meets_goal'] else 'below goal'})"
        )
        lines.append(
            f"  Samples: {target['samples']} "
            f"(healthy {target['healthy']}, "
            f"unhealthy {target['unhealthy']}, errors {target['errors']})"
        )
        lines.append(
            f"  Duration: avg {target['average_duration_ms']} ms, "
            f"max {target['maximum_duration_ms']} ms"
        )
        lines.append(
            f"  Window: {target['first_checked_at']} to "
            f"{target['last_checked_at']}"
        )
    return "\n".join(lines).rstrip() + "\n"
