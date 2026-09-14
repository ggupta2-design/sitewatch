"""Strict JSON configuration loading for SiteWatch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Target
from .safety import SiteWatchError


_ROOT_FIELDS = {"schema_version", "targets"}
_TARGET_FIELDS = {
    "name",
    "url",
    "expected_statuses",
    "timeout_seconds",
    "max_bytes",
    "expected_content_type",
    "allow_redirects",
}


def target_from_dict(payload: Any, *, index: int = 0) -> Target:
    if not isinstance(payload, dict) or set(payload) != _TARGET_FIELDS:
        raise SiteWatchError(
            f"targets[{index}] must contain exactly the supported fields"
        )
    statuses = payload["expected_statuses"]
    if not isinstance(statuses, list):
        raise SiteWatchError(f"targets[{index}].expected_statuses must be a list")
    return Target(
        name=payload["name"],
        url=payload["url"],
        expected_statuses=tuple(statuses),
        timeout_seconds=payload["timeout_seconds"],
        max_bytes=payload["max_bytes"],
        expected_content_type=payload["expected_content_type"],
        allow_redirects=payload["allow_redirects"],
    )


def config_from_dict(payload: Any) -> tuple[Target, ...]:
    """Build a bounded target collection from a strict versioned object."""

    if not isinstance(payload, dict) or set(payload) != _ROOT_FIELDS:
        raise SiteWatchError("config must contain exactly the supported fields")
    if payload["schema_version"] != 1:
        raise SiteWatchError(
            f"unsupported schema_version: {payload['schema_version']}"
        )
    raw_targets = payload["targets"]
    if not isinstance(raw_targets, list):
        raise SiteWatchError("targets must be a list")
    if not 1 <= len(raw_targets) <= 100:
        raise SiteWatchError("targets must contain from 1 to 100 entries")

    targets = tuple(
        target_from_dict(item, index=index)
        for index, item in enumerate(raw_targets)
    )
    names = [item.name.casefold() for item in targets]
    if len(names) != len(set(names)):
        raise SiteWatchError("target names must be unique")
    return targets


def load_config(path: str | Path) -> tuple[Target, ...]:
    """Read one UTF-8 configuration file without environment expansion."""

    source = Path(path)
    if not source.exists():
        raise SiteWatchError("config file does not exist")
    if not source.is_file():
        raise SiteWatchError("config path is not a file")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise SiteWatchError("config is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise SiteWatchError(
            f"config is not valid JSON at line {exc.lineno}"
        ) from exc
    except OSError as exc:
        raise SiteWatchError("could not read config") from exc
    return config_from_dict(payload)
