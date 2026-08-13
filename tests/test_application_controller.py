from __future__ import annotations

import os
import threading
import time
import uuid
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtCore, QtNetwork, QtWidgets

from app.application_controller import (
    MAX_IPC_MESSAGE_BYTES,
    InstanceStartResult,
    SingleInstanceController,
    resolve_second_launch_command,
    single_instance_server_name,
)


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_server_name_is_stable_per_user_and_suffix_isolated() -> None:
    base = single_instance_server_name()

    assert base.startswith("io.github.toolbox.Toolbox-")
    assert single_instance_server_name("test") == f"{base}-test"


def test_second_controller_notifies_primary_instance() -> None:
    app = _application()
    name = single_instance_server_name(f"pytest-{uuid.uuid4().hex[:8]}")
    QtNetwork.QLocalServer.removeServer(name)
    primary = SingleInstanceController(name)
    activation_count = 0
    secondary_results: list[InstanceStartResult] = []
    secondary_errors: list[BaseException] = []

    def activated() -> None:
        nonlocal activation_count
        activation_count += 1

    primary.activation_requested.connect(activated)

    def notify_from_secondary_process_thread() -> None:
        secondary = SingleInstanceController(name)
        try:
            secondary_results.append(secondary.start())
        except BaseException as exc:  # pragma: no cover - re-raised in the test thread
            secondary_errors.append(exc)
        finally:
            secondary._server.close()

    try:
        assert primary.start() is InstanceStartResult.PRIMARY
        secondary_thread = threading.Thread(
            target=notify_from_secondary_process_thread,
            name="toolbox-secondary-instance-test",
        )
        secondary_thread.start()
        deadline = time.monotonic() + 2
        while (
            (activation_count == 0 or secondary_thread.is_alive())
            and time.monotonic() < deadline
        ):
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
        secondary_thread.join(timeout=0.5)
        assert secondary_errors == []
        assert secondary_results == [InstanceStartResult.SECONDARY]
        assert activation_count == 1
    finally:
        primary._server.close()
        QtNetwork.QLocalServer.removeServer(name)


def test_stale_endpoint_is_removed_only_after_retry() -> None:
    name = single_instance_server_name(f"stale-{uuid.uuid4().hex[:8]}")
    controller = SingleInstanceController(name)
    with (
        patch.object(controller, "_notify_existing", side_effect=[False, False]) as notify,
        patch.object(controller._server, "listen", side_effect=[False, True]) as listen,
        patch.object(QtNetwork.QLocalServer, "removeServer") as remove,
    ):
        result = controller.start()

    assert result is InstanceStartResult.PRIMARY
    assert notify.call_count == 2
    assert listen.call_count == 2
    remove.assert_called_once_with(name)


def test_hard_server_failure_is_not_reported_as_secondary_success() -> None:
    name = single_instance_server_name(f"failure-{uuid.uuid4().hex[:8]}")
    controller = SingleInstanceController(name)
    with (
        patch.object(controller, "_notify_existing", return_value=False),
        patch.object(controller._server, "listen", return_value=False),
        patch.object(QtNetwork.QLocalServer, "removeServer"),
    ):
        result = controller.start()

    assert result is InstanceStartResult.FAILED


def test_versioned_command_supports_partial_reads() -> None:
    _application()
    controller = SingleInstanceController("unused")
    client = MagicMock()
    encoded = controller.encode_command("new_window")
    client.readAll.side_effect = [encoded[:8], encoded[8:]]
    received: list[str] = []
    controller.command_received.connect(lambda command, _payload: received.append(command))

    controller._read_client(client)
    assert received == []
    controller._read_client(client)
    assert received == ["new_window"]


def test_unknown_and_oversized_ipc_messages_are_rejected() -> None:
    controller = SingleInstanceController("unused")
    with pytest.raises(ValueError):
        controller.encode_command("unknown")
    with pytest.raises(ValueError):
        controller.encode_command("activate", "x" * MAX_IPC_MESSAGE_BYTES)


@pytest.mark.parametrize(
    ("arguments", "persisted", "expected"),
    [
        ([], "activate_existing", "activate"),
        ([], "new_window", "new_window"),
        (["--new-window"], "activate_existing", "new_window"),
        (["--activate-existing"], "new_window", "activate"),
        (["--new-window", "--activate-existing"], "activate_existing", "new_window"),
        ([], "invalid", "activate"),
    ],
)
def test_second_launch_command_resolution(arguments, persisted, expected) -> None:
    assert resolve_second_launch_command(arguments, persisted) == expected
