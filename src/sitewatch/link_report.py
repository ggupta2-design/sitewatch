"""Privacy-aware reports for bounded link audits."""

from __future__ import annotations

import json
from typing import Any

from .links import LinkAudit


def link_audit_to_dict(
    audit: LinkAudit,
    *,
    redact_urls: bool = False,
) -> dict[str, Any]:
    """Return stable link metadata without page or response content."""

    links = []
    for result in audit.results:
        item: dict[str, Any] = {
            "state": result.state.value,
            "status": result.status,
            "duration_ms": result.duration_ms,
            "error_code": result.error_code,
        }
        if not redact_urls:
            item["url"] = result.url
            item["final_url"] = result.final_url
        links.append(item)

    payload: dict[str, Any] = {
        "healthy": audit.healthy,
        "source_error": audit.source_error,
        "summary": {
            "discovered": audit.discovered,
            "checked": len(audit.results),
            "healthy": audit.healthy_count,
            "broken": audit.broken_count,
            "errors": audit.error_count,
            "skipped_external": audit.skipped_external,
            "skipped_unsupported": audit.skipped_unsupported,
            "truncated": audit.truncated,
        },
        "links": links,
    }
    if not redact_urls:
        payload["source_url"] = audit.source_url
        payload["final_source_url"] = audit.final_source_url
    return payload


def format_link_audit(
    audit: LinkAudit,
    *,
    as_json: bool = False,
    redact_urls: bool = False,
) -> str:
    """Format one link audit for people or automation."""

    payload = link_audit_to_dict(audit, redact_urls=redact_urls)
    if as_json:
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    summary = payload["summary"]
    lines = [
        "SiteWatch link audit",
        f"Status: {'healthy' if audit.healthy else 'attention required'}",
        f"Discovered: {summary['discovered']}",
        f"Checked: {summary['checked']}",
        f"Healthy: {summary['healthy']}",
        f"Broken: {summary['broken']}",
        f"Errors: {summary['errors']}",
        f"Skipped external: {summary['skipped_external']}",
        f"Skipped unsupported: {summary['skipped_unsupported']}",
        f"Truncated: {'yes' if summary['truncated'] else 'no'}",
    ]
    if not redact_urls:
        lines.insert(2, f"Source URL: {payload['source_url']}")
        if (
            payload["final_source_url"] is not None
            and payload["final_source_url"] != payload["source_url"]
        ):
            lines.insert(3, f"Final source URL: {payload['final_source_url']}")
    if audit.source_error:
        lines.append(f"Source error: {audit.source_error}")
    if payload["links"]:
        lines.append("")
    for index, item in enumerate(payload["links"], start=1):
        label = item.get("url", f"link-{index}")
        lines.append(f"{label}: {item['state']}")
        lines.append(
            f"  Status: {item['status'] if item['status'] is not None else 'none'}"
        )
        if item["error_code"]:
            lines.append(f"  Error: {item['error_code']}")
    return "\n".join(lines).rstrip() + "\n"
