"""Privacy-aware reports for SiteWatch baseline comparisons."""

from __future__ import annotations

import json
from typing import Any

from .drift import DriftRun


def drift_run_to_dict(
    run: DriftRun,
    *,
    redact_urls: bool = False,
) -> dict[str, Any]:
    """Return stable change metadata without old or new response values."""

    targets = []
    for result in run.results:
        item: dict[str, Any] = {
            "name": result.name,
            "state": result.state.value,
            "changed_fields": list(result.changed_fields),
        }
        if not redact_urls:
            item["configured_url"] = result.configured_url
        targets.append(item)
    return {
        "drift": run.has_drift,
        "current_healthy": run.current_healthy,
        "summary": {
            "targets": len(run.results),
            "unchanged": run.unchanged_count,
            "changed": run.changed_count,
            "new": run.new_count,
            "missing": run.missing_count,
        },
        "targets": targets,
    }


def format_drift_run(
    run: DriftRun,
    *,
    as_json: bool = False,
    redact_urls: bool = False,
) -> str:
    """Format a comparison for people or automation."""

    payload = drift_run_to_dict(run, redact_urls=redact_urls)
    if as_json:
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    lines = [
        "SiteWatch baseline comparison",
        f"Status: {'changed' if run.has_drift else 'unchanged'}",
        f"Current health: {'healthy' if run.current_healthy else 'unhealthy'}",
        f"Targets: {len(run.results)}",
        f"Unchanged: {run.unchanged_count}",
        f"Changed: {run.changed_count}",
        f"New: {run.new_count}",
        f"Missing: {run.missing_count}",
        "",
    ]
    for item in payload["targets"]:
        lines.append(f"{item['name']}: {item['state']}")
        if not redact_urls:
            lines.append(f"  URL: {item['configured_url']}")
        lines.append(
            "  Changed fields: "
            + (
                ", ".join(item["changed_fields"])
                if item["changed_fields"]
                else "none"
            )
        )
    return "\n".join(lines).rstrip() + "\n"
