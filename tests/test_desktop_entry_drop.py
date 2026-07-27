from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

from app.domain.models import ToolboxEntry
from app.features.entries.launching import MainWindowEntryLaunchingMixin
from app.services.desktop_entries import DesktopLaunchInput
from app.ui.widgets.canvas_widgets import ToolTileWidget


def _app() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _desktop(tmp_path: Path, exec_line: str, *, extra: str = "") -> Path:
    path = tmp_path / "Drop.desktop"
    path.write_text(
        (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Drop Test\n"
            f"Exec={exec_line}\n"
            f"{extra}"
        ),
        encoding="utf-8",
    )
    return path


def _tile(path: Path) -> ToolTileWidget:
    _app()
    entry = ToolboxEntry(title="Drop Test", path=str(path))
    return ToolTileWidget(entry, QtGui.QIcon(), 64)


def _drag_event(mime_data: QtCore.QMimeData) -> QtGui.QDragEnterEvent:
    return QtGui.QDragEnterEvent(
        QtCore.QPoint(4, 4),
        QtCore.Qt.DropAction.CopyAction,
        mime_data,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )


def _drop_event(mime_data: QtCore.QMimeData) -> QtGui.QDropEvent:
    return QtGui.QDropEvent(
        QtCore.QPointF(4, 4),
        QtCore.Qt.DropAction.CopyAction,
        mime_data,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )


def test_percent_f_tile_accepts_local_file_drag(tmp_path: Path) -> None:
    desktop = _desktop(tmp_path, "/usr/bin/true %F")
    tile = _tile(desktop)
    mime_data = QtCore.QMimeData()
    mime_data.setUrls([QtCore.QUrl.fromLocalFile(str(tmp_path / "one.txt"))])
    event = _drag_event(mime_data)

    tile.dragEnterEvent(event)

    assert event.isAccepted()
    assert tile.property("external_drop_state") == "valid"


def test_percent_f_tile_marks_remote_url_invalid(tmp_path: Path) -> None:
    desktop = _desktop(tmp_path, "/usr/bin/true %F")
    tile = _tile(desktop)
    mime_data = QtCore.QMimeData()
    mime_data.setUrls([QtCore.QUrl("https://example.com/file")])
    event = _drag_event(mime_data)

    tile.dragEnterEvent(event)

    assert event.isAccepted()
    assert tile.property("external_drop_state") == "invalid"


def test_tile_without_file_code_marks_drop_invalid(tmp_path: Path) -> None:
    desktop = _desktop(tmp_path, "/usr/bin/true")
    tile = _tile(desktop)
    mime_data = QtCore.QMimeData()
    mime_data.setUrls([QtCore.QUrl.fromLocalFile(str(tmp_path / "one.txt"))])
    event = _drag_event(mime_data)

    tile.dragEnterEvent(event)

    assert event.isAccepted()
    assert tile.property("external_drop_state") == "invalid"


def test_tile_marks_declared_mime_mismatch_invalid(tmp_path: Path) -> None:
    desktop = _desktop(
        tmp_path,
        "/usr/bin/true %F",
        extra="MimeType=application/x-mswinurl;\n",
    )
    tile = _tile(desktop)
    dropped = tmp_path / "plain.txt"
    dropped.write_text("text", encoding="utf-8")
    mime_data = QtCore.QMimeData()
    mime_data.setUrls([QtCore.QUrl.fromLocalFile(str(dropped))])
    event = _drag_event(mime_data)

    tile.dragEnterEvent(event)

    assert event.isAccepted()
    assert tile.property("external_drop_state") == "invalid"


def test_drop_emits_entry_id_and_ordered_payload(tmp_path: Path) -> None:
    desktop = _desktop(tmp_path, "/usr/bin/true %U")
    tile = _tile(desktop)
    local_path = tmp_path / "one file.txt"
    mime_data = QtCore.QMimeData()
    mime_data.setUrls(
        [
            QtCore.QUrl.fromLocalFile(str(local_path)),
            QtCore.QUrl("https://example.com/a%20b"),
        ]
    )
    payloads: list[tuple[str, object]] = []
    tile.files_dropped.connect(
        lambda entry_id, payload: payloads.append((entry_id, payload))
    )
    event = _drop_event(mime_data)

    tile.dropEvent(event)

    assert event.isAccepted()
    assert len(payloads) == 1
    entry_id, payload = payloads[0]
    assert entry_id == tile.entry.entry_id
    assert payload[0]["local_path"] == str(local_path)
    assert payload[1]["url"] == "https://example.com/a%20b"
    assert tile.property("external_drop_state") == "none"


def test_drag_leave_clears_highlight(tmp_path: Path) -> None:
    desktop = _desktop(tmp_path, "/usr/bin/true %U")
    tile = _tile(desktop)
    tile.setProperty("external_drop_state", "valid")
    event = QtGui.QDragLeaveEvent()

    tile.dragLeaveEvent(event)

    assert tile.property("external_drop_state") == "none"


def test_controller_converts_drop_payload_without_adding_an_entry(
    tmp_path: Path,
) -> None:
    desktop = _desktop(tmp_path, "/usr/bin/true %F")
    dropped = tmp_path / "input.txt"
    dropped.write_text("safe", encoding="utf-8")
    entry = ToolboxEntry(title="Drop Test", path=str(desktop))
    context = SimpleNamespace(entries=[entry])
    owner = MagicMock()

    MainWindowEntryLaunchingMixin._on_entry_files_dropped(
        owner,
        context,
        entry.entry_id,
        (
            {
                "url": QtCore.QUrl.fromLocalFile(str(dropped)).toString(),
                "local_path": str(dropped),
            },
        ),
    )

    owner._launch_entry_with_drop.assert_called_once()
    launch_input = owner._launch_entry_with_drop.call_args.args[2]
    assert isinstance(launch_input, DesktopLaunchInput)
    assert launch_input.items[0].local_path == str(dropped)
    assert launch_input.items[0].mime_type
    assert context.entries == [entry]


def test_drop_status_distinguishes_gio_delegation_from_direct_launch(
    tmp_path: Path,
) -> None:
    desktop = _desktop(tmp_path, "/usr/bin/true %U")
    entry = ToolboxEntry(title="Drop Test", path=str(desktop))
    launch_input = DesktopLaunchInput.from_local_paths((tmp_path / "input.txt",))
    context = SimpleNamespace()
    owner = SimpleNamespace(
        status=MagicMock(),
        desktop_process_manager=MagicMock(),
        _entry_target_log_label=lambda item: item.title,
        _update_details=MagicMock(),
    )

    with patch(
        "app.features.entries.launching.prepare_desktop_launch",
        return_value=SimpleNamespace(mode="gio"),
    ):
        MainWindowEntryLaunchingMixin._launch_entry_with_drop(
            owner,
            context,
            entry,
            launch_input,
        )

    owner.desktop_process_manager.launch_prepared.assert_called_once()
    final_message = owner.status.showMessage.call_args_list[-1].args[0]
    assert "delegated" in final_message
    assert "1 dropped item(s)" in final_message
    assert "Launched" not in final_message


def test_long_running_drop_failure_does_not_open_modal_dialog() -> None:
    owner = SimpleNamespace(status=MagicMock())

    with patch("app.features.entries.launching.QtWidgets.QMessageBox.critical") as critical:
        MainWindowEntryLaunchingMixin._on_desktop_launch_failed(
            owner,
            "/tmp/Failure.desktop",
            "Failure",
            "Failure exited with code 7.",
            False,
        )

    critical.assert_not_called()
    assert "Launch failed" in owner.status.showMessage.call_args.args[0]
