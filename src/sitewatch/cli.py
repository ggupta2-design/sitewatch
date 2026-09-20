"""SiteWatch command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .availability import summarize_availability
from .availability_report import format_availability_summary
from .baseline import baseline_from_run, format_baseline, load_baseline
from .checks import run_checks
from .config import load_config
from .drift import compare_to_baseline
from .drift_report import format_drift_run
from .link_http import check_link_destination, fetch_html_page
from .link_report import format_link_audit
from .links import LinkAuditPolicy, audit_links
from .incident_report import format_incident_analysis
from .incidents import analyze_incidents
from .history import (
    append_history,
    format_history,
    history_from_run,
    load_history,
)
from .output import write_output
from .reliability import evaluate_reliability
from .reliability_policy import load_policy, policy_to_dict
from .reliability_report import format_alert_decision
from .report import format_check_run
from .safety import SiteWatchError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sitewatch",
        description="Run safe, bounded website health checks",
    )
    parser.add_argument("--version", action="version", version="sitewatch 0.5.0")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser(
        "validate",
        help="validate a configuration without making network requests",
    )
    validate.add_argument("config", type=Path)
    validate.add_argument("--json", action="store_true", dest="as_json")

    check = commands.add_parser("check", help="run configured health checks")
    check.add_argument("config", type=Path)
    _add_report_options(check)

    snapshot = commands.add_parser(
        "snapshot",
        help="check targets and create a non-overwriting baseline",
    )
    snapshot.add_argument("config", type=Path)
    snapshot.add_argument("--output", type=Path, required=True)

    compare = commands.add_parser(
        "compare",
        help="check targets and compare them with a saved baseline",
    )
    compare.add_argument("config", type=Path)
    compare.add_argument("baseline", type=Path)
    _add_report_options(compare)

    validate_baseline = commands.add_parser(
        "validate-baseline",
        help="validate a baseline without making network requests",
    )
    validate_baseline.add_argument("baseline", type=Path)
    validate_baseline.add_argument("--json", action="store_true", dest="as_json")

    links = commands.add_parser(
        "links",
        help="discover and check bounded links from one public HTML page",
    )
    links.add_argument("url")
    links.add_argument("--max-links", type=int, default=50)
    links.add_argument("--max-page-bytes", type=int, default=1_000_000)
    links.add_argument("--timeout-seconds", type=float, default=10.0)
    links.add_argument("--include-external", action="store_true")
    _add_report_options(links)

    history_create = commands.add_parser(
        "history-create",
        help="check targets and create a new bounded history file",
    )
    history_create.add_argument("config", type=Path)
    history_create.add_argument("--output", type=Path, required=True)

    history_append = commands.add_parser(
        "history-append",
        help="check targets and write a new history from an existing history",
    )
    history_append.add_argument("config", type=Path)
    history_append.add_argument("history", type=Path)
    history_append.add_argument("--output", type=Path, required=True)

    history_validate = commands.add_parser(
        "history-validate",
        help="validate history without making network requests",
    )
    history_validate.add_argument("history", type=Path)
    history_validate.add_argument("--json", action="store_true", dest="as_json")

    availability = commands.add_parser(
        "availability",
        help="summarize bounded history without network requests",
    )
    availability.add_argument("history", type=Path)
    availability.add_argument(
        "--minimum-availability", type=float, default=99.0
    )
    availability.add_argument("--json", action="store_true", dest="as_json")
    availability.add_argument("--output", type=Path)

    incidents = commands.add_parser(
        "incidents",
        help="analyze incidents and monitoring gaps without network requests",
    )
    incidents.add_argument("history", type=Path)
    incidents.add_argument("--maximum-gap-seconds", type=int, default=3600)
    incidents.add_argument("--json", action="store_true", dest="as_json")
    incidents.add_argument("--fail-on-any-incident", action="store_true")
    incidents.add_argument("--output", type=Path)

    policy_validate = commands.add_parser(
        "policy-validate",
        help="validate a reliability policy without network requests",
    )
    policy_validate.add_argument("policy", type=Path)
    policy_validate.add_argument("--json", action="store_true", dest="as_json")

    policy_check = commands.add_parser(
        "policy-check",
        help="evaluate history against a local reliability policy",
    )
    policy_check.add_argument("history", type=Path)
    policy_check.add_argument("policy", type=Path)
    policy_check.add_argument("--json", action="store_true", dest="as_json")
    policy_check.add_argument("--output", type=Path)
    return parser


def _add_report_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--redact-urls", action="store_true")
    parser.add_argument("--output", type=Path)


def _validation_report(targets, *, as_json: bool) -> str:
    payload = {
        "valid": True,
        "targets": len(targets),
        "names": [target.name for target in targets],
    }
    if as_json:
        return json.dumps(payload, indent=2, sort_keys=True)
    return (
        "SiteWatch configuration is valid\n"
        f"Targets: {len(targets)}\n"
        "Names: " + ", ".join(payload["names"])
    )


def _baseline_validation_report(baseline, *, as_json: bool) -> str:
    payload = {
        "valid": True,
        "targets": len(baseline.entries),
        "names": [entry.name for entry in baseline.entries],
    }
    if as_json:
        return json.dumps(payload, indent=2, sort_keys=True)
    return (
        "SiteWatch baseline is valid\n"
        f"Targets: {len(baseline.entries)}\n"
        "Names: " + ", ".join(payload["names"])
    )


def _history_validation_report(history, *, as_json: bool) -> str:
    names = sorted({sample.name for sample in history.samples}, key=str.casefold)
    payload = {
        "valid": True,
        "samples": len(history.samples),
        "targets": len(names),
        "names": names,
    }
    if as_json:
        return json.dumps(payload, indent=2, sort_keys=True)
    return (
        "SiteWatch history is valid\n"
        f"Samples: {len(history.samples)}\n"
        f"Targets: {len(names)}\n"
        "Names: " + ", ".join(names)
    )



def _policy_validation_report(policy, *, as_json: bool) -> str:
    payload = {"valid": True, **policy_to_dict(policy)}
    if as_json:
        return json.dumps(payload, indent=2, sort_keys=True)
    return (
        "SiteWatch reliability policy is valid\n"
        f"Name: {policy.name}\n"
        f"Minimum availability: {policy.minimum_availability:g}%\n"
        f"Maximum open incidents: {policy.maximum_open_incidents}\n"
        f"Maximum monitoring gaps: {policy.maximum_monitoring_gaps}\n"
        f"Maximum errors: {policy.maximum_errors}\n"
        f"Maximum gap: {policy.maximum_gap_seconds} seconds"
    )

def _emit_or_write(content: str, output: Path | None) -> None:
    if output is None:
        print(content, end="" if content.endswith("\n") else "\n")
    else:
        destination = write_output(output, content)
        print(f"Wrote {destination.name}")


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "policy-check":
            decision = evaluate_reliability(
                load_history(args.history),
                load_policy(args.policy),
            )
            content = format_alert_decision(
                decision,
                as_json=args.as_json,
            )
            _emit_or_write(content, args.output)
            return 1 if decision.alert else 0

        if args.command == "policy-validate":
            policy = load_policy(args.policy)
            print(_policy_validation_report(policy, as_json=args.as_json))
            return 0

        if args.command == "validate-baseline":
            baseline = load_baseline(args.baseline)
            print(_baseline_validation_report(baseline, as_json=args.as_json))
            return 0

        if args.command == "history-validate":
            history = load_history(args.history)
            print(_history_validation_report(history, as_json=args.as_json))
            return 0

        if args.command == "incidents":
            analysis = analyze_incidents(
                load_history(args.history),
                maximum_gap_seconds=args.maximum_gap_seconds,
            )
            content = format_incident_analysis(
                analysis,
                as_json=args.as_json,
            )
            _emit_or_write(content, args.output)
            strict_failure = args.fail_on_any_incident and analysis.incident_count > 0
            return 1 if analysis.attention_required or strict_failure else 0

        if args.command == "availability":
            summary = summarize_availability(
                load_history(args.history),
                minimum_availability=args.minimum_availability,
            )
            content = format_availability_summary(
                summary,
                as_json=args.as_json,
            )
            _emit_or_write(content, args.output)
            return 0 if summary.meets_goal else 1

        if args.command == "links":
            policy = LinkAuditPolicy(
                source_url=args.url,
                max_links=args.max_links,
                max_page_bytes=args.max_page_bytes,
                timeout_seconds=args.timeout_seconds,
                include_external=args.include_external,
            )
            audit = audit_links(
                policy,
                fetch_page=fetch_html_page,
                check_link=check_link_destination,
            )
            content = format_link_audit(
                audit,
                as_json=args.as_json,
                redact_urls=args.redact_urls,
            )
            _emit_or_write(content, args.output)
            return 0 if audit.healthy else 1

        targets = load_config(args.config)
        if args.command == "validate":
            print(_validation_report(targets, as_json=args.as_json))
            return 0

        result = run_checks(targets)
        if args.command == "history-create":
            destination = write_output(
                args.output, format_history(history_from_run(result))
            )
            print(f"Wrote {destination.name}")
            return 0 if result.healthy else 1

        if args.command == "history-append":
            history = append_history(load_history(args.history), result)
            destination = write_output(args.output, format_history(history))
            print(f"Wrote {destination.name}")
            return 0 if result.healthy else 1

        if args.command == "snapshot":
            destination = write_output(
                args.output, format_baseline(baseline_from_run(result))
            )
            print(f"Wrote {destination.name}")
            return 0 if result.healthy else 1

        if args.command == "compare":
            comparison = compare_to_baseline(result, load_baseline(args.baseline))
            content = format_drift_run(
                comparison,
                as_json=args.as_json,
                redact_urls=args.redact_urls,
            )
            _emit_or_write(content, args.output)
            return 0 if comparison.current_healthy and not comparison.has_drift else 1

        content = format_check_run(
            result,
            as_json=args.as_json,
            redact_urls=args.redact_urls,
        )
        _emit_or_write(content, args.output)
        return 0 if result.healthy else 1
    except SiteWatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
