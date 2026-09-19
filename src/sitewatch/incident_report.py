"""Privacy-aware reports for incident and monitoring-gap analysis."""

from __future__ import annotations

import json
from typing import Any

from .incidents import IncidentAnalysis


def _timestamp(value) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def incident_analysis_to_dict(analysis: IncidentAnalysis) -> dict[str, Any]:
    """Return history insights without URLs, statuses, or error details."""

    return {
        "attention_required": analysis.attention_required,
        "maximum_gap_seconds": analysis.maximum_gap_seconds,
        "summary": {
            "incidents": analysis.incident_count,
            "recovered": analysis.recovered_count,
            "open": analysis.open_count,
            "monitoring_gaps": analysis.gap_count,
            "affected_samples": analysis.affected_samples,
            "unhealthy_samples": analysis.unhealthy_samples,
            "error_samples": analysis.error_samples,
        },
        "incidents": [
            {
                "name": incident.name,
                "started_at": _timestamp(incident.started_at),
                "last_failure_at": _timestamp(incident.last_failure_at),
                "recovered_at": _timestamp(incident.recovered_at),
                "open": incident.open,
                "samples": incident.samples,
                "unhealthy_samples": incident.unhealthy_samples,
                "error_samples": incident.error_samples,
                "maximum_duration_ms": incident.maximum_duration_ms,
                "observed_seconds": incident.observed_seconds,
            }
            for incident in analysis.incidents
        ],
        "monitoring_gaps": [
            {
                "name": gap.name,
                "previous_checked_at": _timestamp(gap.previous_checked_at),
                "next_checked_at": _timestamp(gap.next_checked_at),
                "seconds": gap.seconds,
            }
            for gap in analysis.gaps
        ],
    }


def format_incident_analysis(
    analysis: IncidentAnalysis,
    *,
    as_json: bool = False,
) -> str:
    """Format deterministic incident insights for people or automation."""

    payload = incident_analysis_to_dict(analysis)
    if as_json:
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    summary = payload["summary"]
    lines = [
        "SiteWatch incident analysis",
        f"Status: {'attention required' if analysis.attention_required else 'clear'}",
        f"Incidents: {summary['incidents']}",
        f"Recovered: {summary['recovered']}",
        f"Open: {summary['open']}",
        f"Affected samples: {summary['affected_samples']}",
        f"Monitoring gaps: {summary['monitoring_gaps']}",
        f"Maximum gap: {analysis.maximum_gap_seconds} seconds",
    ]
    if payload["incidents"]:
        lines.extend(["", "Incident timeline"])
        for incident in payload["incidents"]:
            state = "open" if incident["open"] else "recovered"
            lines.append(
                f"- {incident['name']}: {state}, {incident['samples']} affected samples"
            )
            lines.append(
                f"  Window: {incident['started_at']} to "
                f"{incident['last_failure_at']}"
            )
            if incident["recovered_at"] is not None:
                lines.append(f"  Recovery observed: {incident['recovered_at']}")
            lines.append(
                f"  Observed span: {incident['observed_seconds']} seconds; "
                f"max duration {incident['maximum_duration_ms']} ms"
            )
    if payload["monitoring_gaps"]:
        lines.extend(["", "Monitoring gaps"])
        for gap in payload["monitoring_gaps"]:
            lines.append(
                f"- {gap['name']}: {gap['seconds']} seconds between "
                f"{gap['previous_checked_at']} and {gap['next_checked_at']}"
            )
    return "\n".join(lines).rstrip() + "\n"
