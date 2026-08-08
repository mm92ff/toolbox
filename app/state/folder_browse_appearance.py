"""Application-wide appearance preferences for browsed folders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path

from PySide6 import QtCore

from app import constants


MAX_FOLDER_ICON_SIZE_OVERRIDES = 250


@dataclass(frozen=True)
class _FolderIconSizeRecord:
    size: int
    last_used_utc: datetime


def normalize_folder_path(path: str | Path) -> str:
    """Return the stable key used for a folder appearance preference."""

    expanded = Path(os.path.expanduser(str(path)))
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    try:
        normalized = expanded.resolve(strict=False)
    except (OSError, RuntimeError):
        normalized = Path(os.path.abspath(str(expanded)))
    return os.path.normpath(str(normalized))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc_datetime(value: object) -> datetime:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.fromtimestamp(0, timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return datetime.fromtimestamp(0, timezone.utc)


def _format_utc_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


class FolderBrowseAppearanceStore(QtCore.QObject):
    """Store validated per-folder icon sizes and broadcast path-local changes."""

    icon_size_changed = QtCore.Signal(str, object)

    def __init__(
        self,
        parent: QtCore.QObject | None = None,
        *,
        max_entries: int = MAX_FOLDER_ICON_SIZE_OVERRIDES,
    ) -> None:
        super().__init__(parent)
        self._records: dict[str, _FolderIconSizeRecord] = {}
        self._max_entries = max(1, int(max_entries))
        self.revision = 0

    @staticmethod
    def _normalize_size(value: object) -> int | None:
        if isinstance(value, bool):
            return None
        try:
            size = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError, OverflowError):
            return None
        return max(constants.MIN_ICON_SIZE, min(constants.MAX_ICON_SIZE, size))

    def get_override(self, path: str | Path) -> int | None:
        key = normalize_folder_path(path)
        record = self._records.get(key)
        if record is None:
            return None
        self._records[key] = _FolderIconSizeRecord(record.size, _utc_now())
        return record.size

    def effective_icon_size(self, path: str | Path, global_size: object) -> int:
        override = self.get_override(path)
        if override is not None:
            return override
        normalized_global = self._normalize_size(global_size)
        return normalized_global or constants.DEFAULT_ICON_SIZE

    def set_icon_size(self, path: str | Path, size: object) -> bool:
        normalized_size = self._normalize_size(size)
        if normalized_size is None:
            return False
        key = normalize_folder_path(path)
        existing = self._records.get(key)
        if existing is not None and existing.size == normalized_size:
            self._records[key] = _FolderIconSizeRecord(normalized_size, _utc_now())
            return False
        self._records[key] = _FolderIconSizeRecord(normalized_size, _utc_now())
        removed_keys = self._prune_oldest()
        self.revision += 1
        for removed_key in removed_keys:
            self.icon_size_changed.emit(removed_key, None)
        self.icon_size_changed.emit(key, normalized_size)
        return True

    def reset_icon_size(self, path: str | Path) -> bool:
        key = normalize_folder_path(path)
        if self._records.pop(key, None) is None:
            return False
        self.revision += 1
        self.icon_size_changed.emit(key, None)
        return True

    def build_snapshot(self) -> dict[str, object]:
        return {
            "icon_size_overrides": {
                path: {
                    "size": record.size,
                    "last_used_utc": _format_utc_datetime(record.last_used_utc),
                }
                for path, record in sorted(self._records.items())
            }
        }

    def load_snapshot(self, data: object) -> bool:
        if not isinstance(data, dict):
            return False
        raw_overrides = data.get("icon_size_overrides")
        if not isinstance(raw_overrides, dict):
            return False

        incoming: dict[str, _FolderIconSizeRecord] = {}
        for raw_path, raw_record in raw_overrides.items():
            if not isinstance(raw_path, str) or not raw_path.strip():
                continue
            if isinstance(raw_record, dict):
                raw_size = raw_record.get("size")
                last_used = _parse_utc_datetime(raw_record.get("last_used_utc"))
            else:
                # Accept the compact path-to-integer shape used by early builds.
                raw_size = raw_record
                last_used = datetime.fromtimestamp(0, timezone.utc)
            normalized_size = self._normalize_size(raw_size)
            if normalized_size is None:
                continue
            incoming[normalize_folder_path(raw_path)] = _FolderIconSizeRecord(
                normalized_size, last_used
            )

        if len(incoming) > self._max_entries:
            newest = sorted(
                incoming.items(), key=lambda item: item[1].last_used_utc, reverse=True
            )[: self._max_entries]
            incoming = dict(newest)
        if incoming == self._records:
            return False

        old_records = self._records
        self._records = incoming
        self.revision += 1
        changed_keys = set(old_records) | set(incoming)
        for key in sorted(changed_keys):
            old_size = old_records.get(key).size if key in old_records else None
            new_size = incoming.get(key).size if key in incoming else None
            if old_size != new_size:
                self.icon_size_changed.emit(key, new_size)
        return True

    def _prune_oldest(self) -> list[str]:
        removed: list[str] = []
        while len(self._records) > self._max_entries:
            oldest_key = min(
                self._records,
                key=lambda key: (self._records[key].last_used_utc, key),
            )
            del self._records[oldest_key]
            removed.append(oldest_key)
        return removed
