#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validation helpers for externally provided entry paths."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_supported_tool_path(raw_path: str) -> Path | None:
    """Return a resolved path for any existing file or folder."""
    candidate = Path(raw_path).expanduser()
    if not candidate.exists():
        return None
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        logger.debug("Could not resolve path '%s': %s", candidate.name or str(candidate), exc)
        return None

    if resolved.is_dir() or resolved.is_file():
        return resolved
    return None
