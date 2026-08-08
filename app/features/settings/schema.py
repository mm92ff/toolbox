#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Declarative schema for interaction and system settings."""

from __future__ import annotations

from dataclasses import dataclass

from app import constants


@dataclass(frozen=True, slots=True)
class SettingSpec:
    section: str
    name: str
    default: bool | str
    accessor: str
    normalizer: str = ""

    @property
    def qsettings_key(self) -> str:
        return f"{self.section}/{self.name}"


SETTING_SPECS = (
    SettingSpec(
        "interaction",
        "tool_launch_mode",
        constants.DEFAULT_LAUNCH_CLICK_MODE,
        "current_tool_launch_mode",
        "_normalize_tool_launch_mode",
    ),
    SettingSpec(
        "interaction",
        "show_tooltips",
        constants.DEFAULT_SHOW_TOOLTIPS,
        "current_show_tooltips",
    ),
    SettingSpec("system", "minimize_to_tray", False, "current_minimize_to_tray"),
    SettingSpec(
        "system",
        "folder_single_click_browse",
        constants.DEFAULT_FOLDER_SINGLE_CLICK_BROWSE,
        "current_folder_single_click_browse",
    ),
    SettingSpec(
        "system",
        "folder_show_file_count",
        constants.DEFAULT_FOLDER_SHOW_FILE_COUNT,
        "current_folder_show_file_count",
    ),
    SettingSpec(
        "system",
        "file_assoc_use_system",
        constants.DEFAULT_FILE_ASSOC_USE_SYSTEM,
        "current_file_assoc_use_system",
    ),
    SettingSpec("system", "file_assoc_audio", "", "current_file_assoc_audio"),
    SettingSpec("system", "file_assoc_video", "", "current_file_assoc_video"),
    SettingSpec("system", "file_assoc_image", "", "current_file_assoc_image"),
    SettingSpec("system", "file_assoc_pdf", "", "current_file_assoc_pdf"),
    SettingSpec("system", "file_assoc_document", "", "current_file_assoc_document"),
)

SETTING_SPEC_BY_NAME = {spec.name: spec for spec in SETTING_SPECS}


def specs_for_section(section: str) -> tuple[SettingSpec, ...]:
    return tuple(spec for spec in SETTING_SPECS if spec.section == section)


def snapshot_schema_sections(owner: object) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for spec in SETTING_SPECS:
        result.setdefault(spec.section, {})[spec.name] = getattr(owner, spec.accessor)()
    return result


def save_schema_settings(settings: object, owner: object) -> None:
    for spec in SETTING_SPECS:
        settings.setValue(spec.qsettings_key, getattr(owner, spec.accessor)())


def _coerce_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def import_schema_settings(
    settings: object,
    owner: object,
    ui_settings: dict[str, object],
) -> None:
    for spec in SETTING_SPECS:
        section = ui_settings.get(spec.section)
        if not isinstance(section, dict):
            continue
        value = section.get(spec.name, spec.default)
        if isinstance(spec.default, bool):
            normalized: object = _coerce_bool(value, spec.default)
        else:
            normalized = str(value).strip()
            if spec.normalizer:
                normalized = getattr(owner, spec.normalizer)(normalized)
        settings.setValue(spec.qsettings_key, normalized)
