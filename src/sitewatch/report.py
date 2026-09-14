"""Deterministic SiteWatch reports."""

from __future__ import annotations

import json
from typing import Any

from .checks import CheckRun


def check_run_to_dict(
    run: CheckRun,
    *,
    redact_urls: bool = False,
) -> dict[str, Any]:
    """Return stable response metadata without response bodies."""

    targets = []
    for result in run.results:
        observation = result.observation
        payload: dict[str, Any] = {
            "name": result.name,
            "state": result.state.value,
            "findings": list(result.findings),
            "status": observation.status,
            "duration_ms": observation.duration_ms,
            "content_type": observation.content_type,
            "bytes_read": observation.bytes_read,
            "sha256": observation.sha256,
            "checked_at": observation.checked_at.isoformat().replace("+00:00", "Z"),
        }
        if not redact_urls:
            payload["configured_url"] = result.configured_url
            payload["final_url"] = observation.final_url
        targets.append(payload)
    return {
        "healthy": run.healthy,
        "summary": {
            "targets": len(run.results),
            "healthy": run.healthy_count,
            "unhealthy": run.unhealthy_count,
        },
        "targets": targets,
    }


def format_check_run(
    run: CheckRun,
    *,
    as_json: bool = False,
    redact_urls: bool = False,
) -> str:
    """Format a health-check run for people or automation."""

    payload = check_run_to_dict(run, redact_urls=redact_urls)
    if as_json:
        return json.dumps(payload, indent=2, sort_keys=True)

    lines = [
        "SiteWatch health check",
        f"Status: {'healthy' if run.healthy else 'unhealthy'}",
        f"Targets: {len(run.results)}",
        f"Healthy: {run.healthy_count}",
        f"Unhealthy: {run.unhealthy_count}",
        "",
    ]
    for item in payload["targets"]:
        lines.append(f"{item['name']}: {item['state']}")
        if not redact_urls:
            lines.append(f"  URL: {item['configured_url']}")
            if item["final_url"] != item["configured_url"]:
                lines.append(f"  Final URL: {item['final_url']}")
        lines.append(f"  Status: {item['status'] if item['status'] else 'none'}")
        lines.append(f"  Duration: {item['duration_ms']} ms")
        lines.append(
            "  Findings: "
            + (", ".join(item["findings"]) if item["findings"] else "none")
        )
    return "\n".join(lines).rstrip() + "\n"
