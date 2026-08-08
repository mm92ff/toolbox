#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Snapshot/read/write helpers for settings persistence."""

from __future__ import annotations

import json
from logging import Logger

from PySide6 import QtCore

from app.features.settings.schema import (
    save_schema_settings,
    snapshot_schema_sections,
)


def build_ui_settings_snapshot(owner: object) -> dict[str, object]:
    geometry_base64 = bytes(owner.saveGeometry().toBase64()).decode("ascii")
    schema_sections = snapshot_schema_sections(owner)
    folder_appearance_store = getattr(owner, "_folder_browse_appearance_store", None)
    folder_browse_settings = (
        folder_appearance_store.build_snapshot()
        if callable(getattr(folder_appearance_store, "build_snapshot", None))
        else {"icon_size_overrides": {}}
    )
    return {
        "window": {
            "width": owner.width(),
            "height": owner.height(),
            "geometry_base64": geometry_base64,
        },
        "tabs": {
            "current_index": owner.tab_widget.currentIndex(),
            "settings_title": owner._settings_title,
            "help_title": owner._help_title,
            "hidden_toolbox_tab_ids": sorted(owner._hidden_toolbox_tab_ids),
            "help_tab_hidden": owner._help_tab_hidden,
        },
        "layout": {
            "icon_size": owner.current_icon_size(),
            "tile_font_auto": owner.current_tile_font_auto(),
            "tile_font_size": owner.current_tile_font_size(),
            "tile_frame_enabled": owner.current_tile_frame_enabled(),
            "image_file_preview_enabled": owner.current_image_file_preview_enabled(),
            "image_file_preview_mode": owner.current_image_file_preview_mode(),
            "preview_overlay_enabled": owner.current_preview_overlay_enabled(),
            "video_file_preview_enabled": owner.current_video_file_preview_enabled(),
            "hover_preview_enabled": owner.current_hover_preview_enabled(),
            "ffmpeg_manual_path": owner.current_ffmpeg_manual_path(),
            "icon_preview_background_color": owner.current_icon_preview_background_color(),
            "tile_frame_thickness": owner.current_tile_frame_thickness(),
            "tile_frame_color": owner.current_tile_frame_color(),
            "tile_highlight_color": owner.current_tile_highlight_color(),
            "grid_spacing_x": owner.current_grid_spacing_x(),
            "grid_spacing_y": owner.current_grid_spacing_y(),
            "auto_compact_left": owner.current_auto_compact_left(),
            "section_font_size": owner.current_section_font_size(),
            "section_line_thickness": owner.current_section_line_thickness(),
            "section_gap_above": owner.current_section_gap_above(),
            "section_gap_below": owner.current_section_gap_below(),
            "section_gap": owner.current_section_gap(),
            "section_line_color": owner.current_section_line_color(),
        },
        "interaction": schema_sections["interaction"],
        "system": schema_sections["system"],
        "folder_browse": folder_browse_settings,
        "toolbox_splitter_sizes": {
            ctx.tab_id: [int(value) for value in ctx.splitter.sizes()] for ctx in owner.toolbox_tabs
        },
    }


def read_persisted_ui_settings(owner: object, logger: Logger) -> dict[str, object] | None:
    settings_file = owner._ui_settings_json_path()
    try:
        payload = owner._read_json_atomic(settings_file)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not load persisted UI settings '%s': %s", settings_file.name, exc)
        return None

    if isinstance(payload, dict):
        schema_version = payload.get("schema_version")
        if schema_version is not None:
            if not isinstance(schema_version, int):
                logger.warning(
                    "Ignoring UI settings '%s': invalid schema_version type '%s'.",
                    settings_file.name,
                    type(schema_version).__name__,
                )
                return None
            if schema_version > 1:
                logger.warning(
                    "Ignoring UI settings '%s': unsupported schema_version '%s'.",
                    settings_file.name,
                    schema_version,
                )
                return None
        raw_ui_settings = payload.get("ui_settings")
        if isinstance(raw_ui_settings, dict):
            return raw_ui_settings
        # Backward compatibility: file may directly contain the snapshot.
        return payload
    return None


def persist_ui_settings_json(owner: object) -> None:
    payload = {
        "schema_version": 1,
        "saved_at_utc": QtCore.QDateTime.currentDateTimeUtc().toString(QtCore.Qt.DateFormat.ISODate),
        "ui_settings": owner._build_ui_settings_snapshot(),
    }
    owner._write_json_atomic(owner._ui_settings_json_path(), payload)


def persist_imported_ui_settings_json(
    owner: object, ui_settings: dict[str, object]
) -> None:
    """Persist a validated profile snapshot before runtime widgets reload it."""

    payload = {
        "schema_version": 1,
        "saved_at_utc": QtCore.QDateTime.currentDateTimeUtc().toString(
            QtCore.Qt.DateFormat.ISODate
        ),
        "ui_settings": ui_settings,
    }
    owner._write_json_atomic(owner._ui_settings_json_path(), payload)


def persist_folder_browse_settings_json(owner: object) -> None:
    """Update only folder-browse settings without rewriting stale window state."""

    settings_path = owner._ui_settings_json_path()
    folder_snapshot = owner._build_ui_settings_snapshot()["folder_browse"]
    try:
        existing = owner._read_json_atomic(settings_path)
    except FileNotFoundError:
        existing = None

    if existing is None:
        ui_settings = owner._build_ui_settings_snapshot()
        payload: dict[str, object] = {"schema_version": 1, "ui_settings": ui_settings}
    elif not isinstance(existing, dict):
        raise OSError("UI settings root is not a JSON object")
    elif isinstance(existing.get("ui_settings"), dict):
        payload = dict(existing)
        ui_settings = dict(existing["ui_settings"])
        ui_settings["folder_browse"] = folder_snapshot
        payload["ui_settings"] = ui_settings
        payload["schema_version"] = 1
    else:
        # Upgrade the legacy direct-snapshot representation to the wrapped format.
        ui_settings = dict(existing)
        ui_settings["folder_browse"] = folder_snapshot
        payload = {"schema_version": 1, "ui_settings": ui_settings}

    payload["saved_at_utc"] = QtCore.QDateTime.currentDateTimeUtc().toString(
        QtCore.Qt.DateFormat.ISODate
    )
    owner._write_json_atomic(settings_path, payload)


def save_settings(owner: object, logger: Logger) -> None:
    if not getattr(owner, "_settings_ready", False):
        return
    settings = QtCore.QSettings()
    manager = getattr(owner, "_window_manager", None)
    persist_window_local = bool(
        manager is None or getattr(manager, "_last_active", None) is owner
    )
    if persist_window_local:
        settings.setValue("geometry", owner.saveGeometry())
        settings.setValue("window/width", owner.width())
        settings.setValue("window/height", owner.height())
        settings.setValue("tabs/current_index", owner.tab_widget.currentIndex())
    settings.setValue("tabs/settings_title", owner._settings_title)
    settings.setValue("tabs/help_title", owner._help_title)
    settings.setValue("tabs/hidden_toolbox_tab_ids", sorted(owner._hidden_toolbox_tab_ids))
    settings.setValue("tabs/help_tab_hidden", owner._help_tab_hidden)

    settings.setValue("layout/icon_size", owner.current_icon_size())
    settings.setValue("layout/tile_font_auto", owner.current_tile_font_auto())
    settings.setValue("layout/tile_font_size", owner.current_tile_font_size())
    settings.setValue("layout/tile_frame_enabled", owner.current_tile_frame_enabled())
    settings.setValue("layout/image_file_preview_enabled", owner.current_image_file_preview_enabled())
    settings.setValue("layout/image_file_preview_mode", owner.current_image_file_preview_mode())
    settings.setValue("layout/preview_overlay_enabled", owner.current_preview_overlay_enabled())
    settings.setValue("layout/video_file_preview_enabled", owner.current_video_file_preview_enabled())
    settings.setValue("layout/hover_preview_enabled", owner.current_hover_preview_enabled())
    settings.setValue("layout/ffmpeg_manual_path", owner.current_ffmpeg_manual_path())
    settings.setValue(
        "layout/icon_preview_background_color",
        owner.current_icon_preview_background_color(),
    )
    settings.setValue("layout/tile_frame_thickness", owner.current_tile_frame_thickness())
    settings.setValue("layout/tile_frame_color", owner.current_tile_frame_color())
    settings.setValue("layout/tile_highlight_color", owner.current_tile_highlight_color())
    settings.setValue("layout/grid_spacing_x", owner.current_grid_spacing_x())
    settings.setValue("layout/grid_spacing_y", owner.current_grid_spacing_y())
    settings.setValue("layout/auto_compact_left", owner.current_auto_compact_left())
    settings.setValue("layout/section_font_size", owner.current_section_font_size())
    settings.setValue("layout/section_line_thickness", owner.current_section_line_thickness())
    settings.setValue("layout/section_gap_above", owner.current_section_gap_above())
    settings.setValue("layout/section_gap_below", owner.current_section_gap_below())
    settings.setValue("layout/section_gap", owner.current_section_gap())
    settings.setValue("layout/section_line_color", owner.current_section_line_color())
    save_schema_settings(settings, owner)

    if persist_window_local:
        for ctx in owner.toolbox_tabs:
            settings.setValue(f"toolbox/{ctx.tab_id}/splitter_sizes", ctx.splitter.sizes())
    settings.sync()
    try:
        owner._persist_ui_settings_json()
    except OSError as exc:
        logger.warning("Could not persist UI settings JSON: %s", exc)
