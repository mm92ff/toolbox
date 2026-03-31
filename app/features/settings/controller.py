#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings behavior composed from focused mixins."""

from __future__ import annotations

from app.features.settings.appearance import MainWindowSettingsAppearanceMixin
from app.features.settings.apply import MainWindowSettingsApplyMixin
from app.features.settings.io import MainWindowSettingsIOMixin
from app.features.settings.profile import MainWindowSettingsProfileMixin
from app.features.settings.section_colors import MainWindowSettingsSectionColorsMixin
from app.features.settings.state import MainWindowSettingsStateMixin


class MainWindowSettingsMixin(
    MainWindowSettingsStateMixin,
    MainWindowSettingsApplyMixin,
    MainWindowSettingsAppearanceMixin,
    MainWindowSettingsSectionColorsMixin,
    MainWindowSettingsProfileMixin,
    MainWindowSettingsIOMixin,
):
    """Aggregate settings-related mixins for MainWindow."""
