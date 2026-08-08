from __future__ import annotations

import os
import time
import uuid
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtNetwork, QtWidgets

from app.application_controller import (
    InstanceStartResult,
    SingleInstanceController,
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
    secondary = SingleInstanceController(name)
    activation_count = 0

    def activated() -> None:
        nonlocal activation_count
        activation_count += 1

    primary.activation_requested.connect(activated)
    try:
        assert primary.start() is InstanceStartResult.PRIMARY
        assert secondary.start() is InstanceStartResult.SECONDARY
        deadline = time.monotonic() + 2
        while activation_count == 0 and time.monotonic() < deadline:
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
        assert activation_count == 1
    finally:
        primary._server.close()
        secondary._server.close()
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
