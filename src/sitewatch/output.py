"""Non-overwriting atomic report output."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .safety import SiteWatchError


def write_output(path: str | Path, content: str) -> Path:
    """Create a UTF-8 report atomically without replacing an existing file."""

    destination = Path(path)
    if destination.exists():
        raise SiteWatchError(f"output already exists: {destination.name}")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if destination.exists():
                raise SiteWatchError(f"output already exists: {destination.name}")
            os.link(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    except SiteWatchError:
        raise
    except OSError as exc:
        raise SiteWatchError(
            f"could not write output: {destination.name}"
        ) from exc
    return destination
