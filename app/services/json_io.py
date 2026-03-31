#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON file I/O helpers with UTF-8 and atomic write semantics."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any


def read_json_utf8(path: Path) -> Any:
    """Read JSON from ``path`` using UTF-8 encoding."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json_utf8_atomic(
    destination: Path,
    payload: Any,
    *,
    ensure_ascii: bool = False,
    indent: int = 2,
) -> None:
    """Write JSON atomically by persisting to temp file then replacing destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp_path = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temp_path = Path(raw_temp_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=ensure_ascii, indent=indent)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, destination)
    finally:
        with suppress(OSError):
            if temp_path.exists():
                temp_path.unlink()
