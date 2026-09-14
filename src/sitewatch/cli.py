"""SiteWatch command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .checks import run_checks
from .config import load_config
from .output import write_output
from .report import format_check_run
from .safety import SiteWatchError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sitewatch",
        description="Run safe, bounded website health checks",
    )
    parser.add_argument("--version", action="version", version="sitewatch 0.1.0")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser(
        "validate",
        help="validate a configuration without making network requests",
    )
    validate.add_argument("config", type=Path)
    validate.add_argument("--json", action="store_true", dest="as_json")

    check = commands.add_parser(
        "check",
        help="run configured health checks",
    )
    check.add_argument("config", type=Path)
    check.add_argument("--json", action="store_true", dest="as_json")
    check.add_argument("--redact-urls", action="store_true")
    check.add_argument("--output", type=Path)
    return parser


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


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        targets = load_config(args.config)
        if args.command == "validate":
            print(_validation_report(targets, as_json=args.as_json))
            return 0

        result = run_checks(targets)
        content = format_check_run(
            result,
            as_json=args.as_json,
            redact_urls=args.redact_urls,
        )
        if args.output is None:
            print(content, end="" if content.endswith("\n") else "\n")
        else:
            destination = write_output(args.output, content)
            print(f"Wrote {destination.name}")
        return 0 if result.healthy else 1
    except SiteWatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
