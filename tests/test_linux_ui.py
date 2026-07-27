from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.domain.models import ToolboxEntry
from app.features.entries.controller_selection import update_details
from app.features.entries.launching import MainWindowEntryLaunchingMixin


def test_linux_launch_ignores_saved_windows_only_options() -> None:
    owner = MagicMock()
    entry = ToolboxEntry(
        title="Legacy Windows entry",
        path="/usr/bin/true",
        always_run_as_admin=True,
        launch_window_style="minimized",
    )

    with (
        patch("app.features.entries.launching.sys.platform", "linux"),
        patch("app.features.entries.launching.launch_path") as launch_path,
    ):
        MainWindowEntryLaunchingMixin._launch_entry(owner, MagicMock(), entry)

    launch_path.assert_called_once()
    assert launch_path.call_args.kwargs["run_as_admin"] is False
    assert launch_path.call_args.kwargs["window_style"] == "normal"


def test_linux_details_hide_admin_and_window_style_text() -> None:
    entry = ToolboxEntry(
        title="Linux tool",
        path="/usr/bin/true",
        always_run_as_admin=True,
        launch_arguments="--help",
        launch_window_style="hidden",
    )
    label = MagicMock()
    context = SimpleNamespace(
        entries=[entry],
        selected_ids={entry.entry_id},
        details_label=label,
    )
    owner = MagicMock()
    owner._entry_has_persistent_launch_options.return_value = True

    with patch("app.features.entries.controller_selection.sys.platform", "linux"):
        update_details(owner, context)

    text = label.setText.call_args.args[0]
    assert "administrator" not in text.lower()
    assert "window style" not in text.lower()
    assert "hidden" not in text.lower()


def test_help_text_is_platform_neutral_for_ffmpeg() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "ui"
        / "tabs"
        / "help_tab.py"
    ).read_text(encoding="utf-8")

    assert "ffmpeg.exe" not in source.lower()
