#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse and expand freedesktop desktop-entry application launchers."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import locale
import os
from pathlib import Path
import re
from typing import Iterable


MAX_DESKTOP_ENTRY_BYTES = 1024 * 1024
_GROUP_NAME = "Desktop Entry"
_KEY_PATTERN = re.compile(r"^[A-Za-z0-9-]+(?:\[[^\]\r\n]+\])?$")
_SUPPORTED_FIELD_CODES = frozenset({"f", "F", "u", "U", "i", "c", "k", "%"})
_DEPRECATED_FIELD_CODES = frozenset({"d", "D", "n", "N", "v", "m"})
_FILE_FIELD_CODES = frozenset({"f", "F", "u", "U"})
_MULTI_ARGUMENT_FIELD_CODES = frozenset({"F", "U", "i"})
_EXEC_RESERVED_OUTSIDE_QUOTES = frozenset("\"'\\><~|&;$*?#()`")
_EXEC_ESCAPABLE_IN_QUOTES = frozenset('"`$\\')


class DesktopEntryError(ValueError):
    """A desktop entry is malformed or cannot be launched safely."""


@dataclass(frozen=True, slots=True)
class DesktopEntryMetadata:
    """Validated metadata from the main ``[Desktop Entry]`` group."""

    source_path: Path
    entry_type: str
    name: str
    icon: str
    exec_line: str
    try_exec: str
    working_directory: str
    terminal: bool
    dbus_activatable: bool
    mime_types: tuple[str, ...]
    hidden: bool
    no_display: bool
    url: str

    @property
    def is_application(self) -> bool:
        return self.entry_type == "Application"

    @property
    def is_link(self) -> bool:
        return self.entry_type == "Link"


@dataclass(frozen=True, slots=True)
class DesktopLaunchItem:
    """One local path or URL supplied to a desktop launcher."""

    url: str
    local_path: str = ""
    mime_type: str = ""

    @classmethod
    def from_local_path(
        cls,
        path: str | Path,
        *,
        mime_type: str = "",
    ) -> "DesktopLaunchItem":
        local_path = str(Path(path).expanduser())
        return cls(
            url=Path(local_path).resolve(strict=False).as_uri(),
            local_path=local_path,
            mime_type=mime_type,
        )


@dataclass(frozen=True, slots=True)
class DesktopLaunchInput:
    """Ordered external inputs dropped on a desktop launcher."""

    items: tuple[DesktopLaunchItem, ...] = ()

    @classmethod
    def from_local_paths(cls, paths: Iterable[str | Path]) -> "DesktopLaunchInput":
        return cls(tuple(DesktopLaunchItem.from_local_path(path) for path in paths))

    def one_item(self, item: DesktopLaunchItem) -> "DesktopLaunchInput":
        return DesktopLaunchInput((item,))


def _desktop_error(path: Path, message: str) -> DesktopEntryError:
    return DesktopEntryError(f"{path.name}: {message}")


def _unescape_desktop_string(value: str, path: Path, key: str) -> str:
    """Apply the first string escaping layer from the desktop-entry spec."""

    result: list[str] = []
    index = 0
    escapes = {
        "s": " ",
        "n": "\n",
        "t": "\t",
        "r": "\r",
        "\\": "\\",
    }
    while index < len(value):
        char = value[index]
        if char != "\\":
            result.append(char)
            index += 1
            continue
        if index + 1 >= len(value):
            raise _desktop_error(path, f"{key} ends with an incomplete escape")
        escaped = value[index + 1]
        replacement = escapes.get(escaped)
        if replacement is None:
            raise _desktop_error(path, f"{key} contains unsupported escape \\{escaped}")
        result.append(replacement)
        index += 2
    return "".join(result)


def _parse_main_group(text: str, path: Path) -> dict[str, str]:
    groups: dict[str, dict[str, str]] = {}
    current_group: str | None = None
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            group_name = line[1:-1].strip()
            if not group_name:
                raise _desktop_error(path, f"empty group name on line {line_number}")
            current_group = group_name
            groups.setdefault(group_name, {})
            continue
        if current_group is None:
            raise _desktop_error(path, f"key outside a group on line {line_number}")
        if "=" not in raw_line:
            raise _desktop_error(path, f"missing '=' on line {line_number}")
        key, value = raw_line.split("=", 1)
        key = key.strip()
        if not _KEY_PATTERN.fullmatch(key):
            raise _desktop_error(path, f"invalid key '{key}' on line {line_number}")
        groups[current_group][key] = value

    main_group = groups.get(_GROUP_NAME)
    if main_group is None:
        raise _desktop_error(path, "missing [Desktop Entry] group")
    return main_group


def _normalize_locale_name(value: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return ""
    normalized = normalized.split(".", 1)[0]
    return normalized.replace("-", "_")


def _locale_candidates(explicit_locale: str | None) -> tuple[str, ...]:
    raw_candidates: list[str] = []
    if explicit_locale is not None:
        raw_candidates.append(explicit_locale)
    else:
        language = os.environ.get("LANGUAGE", "")
        if language:
            raw_candidates.extend(language.split(":"))
        for env_name in ("LC_ALL", "LC_MESSAGES", "LANG"):
            value = os.environ.get(env_name, "")
            if value:
                raw_candidates.append(value)
        try:
            detected = locale.getlocale()[0]
        except (TypeError, ValueError):
            detected = None
        if detected:
            raw_candidates.append(detected)

    candidates: list[str] = []
    for raw in raw_candidates:
        normalized = _normalize_locale_name(raw)
        if not normalized or normalized in {"C", "POSIX"}:
            continue
        if normalized not in candidates:
            candidates.append(normalized)
        base, separator, modifier = normalized.partition("@")
        if separator:
            if base not in candidates:
                candidates.append(base)
            language, territory_separator, _territory = base.partition("_")
            language_with_modifier = f"{language}@{modifier}"
            if territory_separator and language_with_modifier not in candidates:
                candidates.append(language_with_modifier)
        language = base.split("_", 1)[0]
        if language and language not in candidates:
            candidates.append(language)
    return tuple(candidates)


def _localized_value(
    values: dict[str, str],
    key: str,
    locale_name: str | None,
    path: Path,
) -> str:
    for candidate in _locale_candidates(locale_name):
        localized_key = f"{key}[{candidate}]"
        if localized_key in values:
            return _unescape_desktop_string(values[localized_key], path, localized_key)
    if key not in values:
        return ""
    return _unescape_desktop_string(values[key], path, key)


def _boolean_value(values: dict[str, str], key: str, path: Path) -> bool:
    raw_value = values.get(key)
    if raw_value is None or not raw_value.strip():
        return False
    value = raw_value.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise _desktop_error(path, f"{key} must be true or false")


def _read_desktop_entry_uncached(
    path_text: str,
    _mtime_ns: int,
    _size: int,
    locale_name: str | None,
) -> DesktopEntryMetadata:
    path = Path(path_text)
    try:
        raw_data = path.read_bytes()
    except OSError as exc:
        raise _desktop_error(path, f"cannot read desktop file: {exc}") from exc
    if len(raw_data) > MAX_DESKTOP_ENTRY_BYTES:
        raise _desktop_error(
            path,
            f"desktop file exceeds {MAX_DESKTOP_ENTRY_BYTES} bytes",
        )
    try:
        text = raw_data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise _desktop_error(path, "desktop file is not valid UTF-8") from exc

    values = _parse_main_group(text, path)
    entry_type = _localized_value(values, "Type", None, path).strip()
    if not entry_type:
        raise _desktop_error(path, "missing Type")
    if entry_type not in {"Application", "Link"}:
        raise _desktop_error(path, f"unsupported Type={entry_type}")

    name = _localized_value(values, "Name", locale_name, path).strip() or path.stem
    icon = _localized_value(values, "Icon", None, path).strip()
    exec_line = _localized_value(values, "Exec", None, path).strip()
    try_exec = _localized_value(values, "TryExec", None, path).strip()
    working_directory = _localized_value(values, "Path", None, path).strip()
    url = _localized_value(values, "URL", None, path).strip()
    dbus_activatable = _boolean_value(values, "DBusActivatable", path)

    if entry_type == "Application" and not exec_line and not dbus_activatable:
        raise _desktop_error(path, "Application entry is missing Exec")
    if entry_type == "Link" and not url:
        raise _desktop_error(path, "Link entry is missing URL")

    raw_mime_types = _localized_value(values, "MimeType", None, path)
    mime_types = tuple(
        item.strip() for item in raw_mime_types.split(";") if item.strip()
    )
    return DesktopEntryMetadata(
        source_path=path,
        entry_type=entry_type,
        name=name,
        icon=icon,
        exec_line=exec_line,
        try_exec=try_exec,
        working_directory=working_directory,
        terminal=_boolean_value(values, "Terminal", path),
        dbus_activatable=dbus_activatable,
        mime_types=mime_types,
        hidden=_boolean_value(values, "Hidden", path),
        no_display=_boolean_value(values, "NoDisplay", path),
        url=url,
    )


_read_desktop_entry_cached = lru_cache(maxsize=512)(_read_desktop_entry_uncached)


def read_desktop_entry(
    filepath: str | Path,
    *,
    locale_name: str | None = None,
) -> DesktopEntryMetadata:
    """Read a desktop file without executing it."""

    path = Path(filepath).expanduser()
    try:
        stat = path.stat()
    except OSError as exc:
        raise _desktop_error(path, f"desktop file is unavailable: {exc}") from exc
    if not path.is_file():
        raise _desktop_error(path, "desktop entry is not a regular file")
    if stat.st_size > MAX_DESKTOP_ENTRY_BYTES:
        raise _desktop_error(
            path,
            f"desktop file exceeds {MAX_DESKTOP_ENTRY_BYTES} bytes",
        )
    return _read_desktop_entry_cached(
        str(path.resolve(strict=False)),
        stat.st_mtime_ns,
        stat.st_size,
        locale_name,
    )


def clear_desktop_entry_cache() -> None:
    """Clear parsed desktop-entry metadata."""

    _read_desktop_entry_cached.cache_clear()


def _tokenize_exec(exec_line: str, path: Path) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    token_started = False
    quoted = False
    just_closed_quote = False
    index = 0

    while index < len(exec_line):
        char = exec_line[index]
        if quoted:
            if char == '"':
                quoted = False
                just_closed_quote = True
                index += 1
                continue
            if char == "\\":
                if index + 1 >= len(exec_line):
                    raise _desktop_error(path, "Exec has an incomplete quoted escape")
                escaped = exec_line[index + 1]
                if escaped not in _EXEC_ESCAPABLE_IN_QUOTES:
                    raise _desktop_error(
                        path,
                        f"Exec contains unsupported quoted escape \\{escaped}",
                    )
                current.append(escaped)
                index += 2
                continue
            if char == "%" and index + 1 < len(exec_line):
                field_candidate = exec_line[index + 1]
                if field_candidate.isalpha():
                    raise _desktop_error(path, "Exec field codes must not be quoted")
            current.append(char)
            index += 1
            continue

        if char.isspace():
            if token_started:
                tokens.append("".join(current))
                current = []
                token_started = False
                just_closed_quote = False
            index += 1
            continue
        if just_closed_quote:
            raise _desktop_error(path, "quoted Exec arguments must be quoted in whole")
        if char == '"':
            if token_started:
                raise _desktop_error(path, "quoted Exec arguments must be quoted in whole")
            token_started = True
            quoted = True
            index += 1
            continue
        if char in _EXEC_RESERVED_OUTSIDE_QUOTES:
            raise _desktop_error(
                path,
                f"Exec reserved character '{char}' must be quoted",
            )
        token_started = True
        current.append(char)
        index += 1

    if quoted:
        raise _desktop_error(path, "Exec contains an unterminated quote")
    if token_started:
        tokens.append("".join(current))
    if not tokens or not tokens[0]:
        raise _desktop_error(path, "Exec does not contain an executable")
    if "=" in tokens[0]:
        raise _desktop_error(path, "Exec executable must not contain '='")
    return tokens


def _field_codes(tokens: Iterable[str], path: Path) -> tuple[str, ...]:
    found: list[str] = []
    for token in tokens:
        index = 0
        while index < len(token):
            if token[index] != "%":
                index += 1
                continue
            if index + 1 >= len(token):
                raise _desktop_error(path, "Exec contains an unescaped '%'")
            code = token[index + 1]
            if not (code.isalpha() or code == "%"):
                raise _desktop_error(path, f"Exec contains invalid field code %{code}")
            if code not in _SUPPORTED_FIELD_CODES and code not in _DEPRECATED_FIELD_CODES:
                raise _desktop_error(path, f"Exec contains unknown field code %{code}")
            found.append(code)
            index += 2
    file_codes = [code for code in found if code in _FILE_FIELD_CODES]
    if len(file_codes) > 1:
        raise _desktop_error(path, "Exec contains more than one file or URL field code")
    return tuple(found)


def desktop_entry_file_field_code(metadata: DesktopEntryMetadata) -> str:
    """Return the entry's file/URL field code, or an empty string."""

    if not metadata.exec_line:
        return ""
    tokens = _tokenize_exec(metadata.exec_line, metadata.source_path)
    for code in _field_codes(tokens, metadata.source_path):
        if code in _FILE_FIELD_CODES:
            return code
    return ""


def desktop_entry_accepts_drop(metadata: DesktopEntryMetadata) -> bool:
    """Return whether an application entry declares a file/URL field code."""

    return metadata.is_application and bool(desktop_entry_file_field_code(metadata))


def validate_desktop_launch_input(
    metadata: DesktopEntryMetadata,
    launch_input: DesktopLaunchInput,
) -> None:
    """Validate locality and declared MIME support for dropped inputs."""

    if not launch_input.items:
        return
    field_code = desktop_entry_file_field_code(metadata)
    if not field_code:
        raise _desktop_error(
            metadata.source_path,
            "this desktop entry does not accept dropped files or URLs",
        )
    if field_code in {"f", "F"} and any(
        not item.local_path for item in launch_input.items
    ):
        raise _desktop_error(
            metadata.source_path,
            f"%{field_code} accepts local files only",
        )

    if not metadata.mime_types:
        return
    accepted = set(metadata.mime_types)
    for item in launch_input.items:
        if not item.local_path or not item.mime_type:
            continue
        if item.mime_type in accepted:
            continue
        if (
            "application/octet-stream" in accepted
            and item.mime_type != "inode/directory"
        ):
            continue
        raise _desktop_error(
            metadata.source_path,
            f"dropped item type '{item.mime_type}' is not declared in MimeType",
        )


def _replace_single_argument_codes(
    token: str,
    metadata: DesktopEntryMetadata,
    launch_input: DesktopLaunchInput,
    file_code: str,
) -> str:
    result: list[str] = []
    index = 0
    while index < len(token):
        char = token[index]
        if char != "%":
            result.append(char)
            index += 1
            continue
        code = token[index + 1]
        index += 2
        if code == "%":
            result.append("%")
        elif code == "c":
            result.append(metadata.name)
        elif code == "k":
            result.append(str(metadata.source_path))
        elif code in _DEPRECATED_FIELD_CODES:
            continue
        elif code == "f":
            if launch_input.items and launch_input.items[0].local_path:
                result.append(launch_input.items[0].local_path)
        elif code == "u":
            if launch_input.items:
                item = launch_input.items[0]
                result.append(item.url or item.local_path)
        elif code in {"F", "U", "i"}:
            raise _desktop_error(
                metadata.source_path,
                f"%{code} must be a standalone Exec argument",
            )
        else:
            raise _desktop_error(
                metadata.source_path,
                f"unsupported field code %{code}",
            )
    return "".join(result)


def expand_desktop_exec(
    metadata: DesktopEntryMetadata,
    launch_input: DesktopLaunchInput | None = None,
) -> tuple[str, ...]:
    """Expand a desktop entry's Exec command into a safe argument tuple."""

    if not metadata.is_application:
        raise _desktop_error(metadata.source_path, "only Application entries have Exec commands")
    launch_input = launch_input or DesktopLaunchInput()
    validate_desktop_launch_input(metadata, launch_input)
    tokens = _tokenize_exec(metadata.exec_line, metadata.source_path)
    codes = _field_codes(tokens, metadata.source_path)
    executable_codes = _field_codes((tokens[0],), metadata.source_path)
    if any(code != "%" for code in executable_codes):
        raise _desktop_error(
            metadata.source_path,
            "Exec executable must not contain field codes",
        )
    file_code = next((code for code in codes if code in _FILE_FIELD_CODES), "")
    if launch_input.items and not file_code:
        raise _desktop_error(
            metadata.source_path,
            "this desktop entry does not accept dropped files or URLs",
        )
    if file_code in {"f", "F"}:
        remote_items = [item for item in launch_input.items if not item.local_path]
        if remote_items:
            raise _desktop_error(
                metadata.source_path,
                f"%{file_code} accepts local files only",
            )

    expanded: list[str] = []
    for token_index, token in enumerate(tokens):
        if token == "%F":
            expanded.extend(
                item.local_path for item in launch_input.items if item.local_path
            )
            continue
        if token == "%U":
            expanded.extend(
                item.url or item.local_path for item in launch_input.items
            )
            continue
        if token == "%i":
            if metadata.icon:
                expanded.extend(("--icon", metadata.icon))
            continue
        value = _replace_single_argument_codes(
            token,
            metadata,
            launch_input,
            file_code,
        )
        if value or token_index == 0:
            expanded.append(value)

    if not expanded or not expanded[0]:
        raise _desktop_error(metadata.source_path, "Exec executable is empty after expansion")
    return tuple(expanded)


def expand_desktop_exec_many(
    metadata: DesktopEntryMetadata,
    launch_input: DesktopLaunchInput | None = None,
) -> tuple[tuple[str, ...], ...]:
    """Return one or more commands according to single-item field-code semantics."""

    launch_input = launch_input or DesktopLaunchInput()
    file_code = desktop_entry_file_field_code(metadata)
    if file_code in {"f", "u"} and len(launch_input.items) > 1:
        return tuple(
            expand_desktop_exec(metadata, launch_input.one_item(item))
            for item in launch_input.items
        )
    return (expand_desktop_exec(metadata, launch_input),)
