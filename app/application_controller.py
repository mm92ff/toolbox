#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Application-level single-instance coordination."""

from __future__ import annotations

import hashlib
import logging
import os
from enum import Enum

from PySide6 import QtCore, QtNetwork

from app import constants


logger = logging.getLogger(__name__)
ACTIVATE_COMMAND = b"ACTIVATE"


class InstanceStartResult(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    FAILED = "failed"


def single_instance_server_name(instance_suffix: str = "") -> str:
    """Return a stable per-user server name with optional test isolation."""

    user_id = str(getattr(os, "getuid", lambda: 0)())
    name = f"{constants.DESKTOP_FILE_NAME}-{user_id}"
    suffix = instance_suffix.strip()
    if not suffix:
        return name
    candidate = f"{name}-{suffix}"
    if len(candidate.encode("utf-8")) <= 64:
        return candidate
    digest = hashlib.sha256(suffix.encode("utf-8")).hexdigest()[:16]
    return f"{name}-{digest}"


class SingleInstanceController(QtCore.QObject):
    """Own the local server and emit activation requests without blocking the GUI."""

    activation_requested = QtCore.Signal()

    def __init__(self, server_name: str, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.server_name = server_name
        self._server = QtNetwork.QLocalServer(self)
        self._server.newConnection.connect(self._handle_connections)
        self._clients: set[QtNetwork.QLocalSocket] = set()

    def start(self) -> InstanceStartResult:
        """Start the primary server, or notify the existing primary instance."""

        if self._notify_existing():
            return InstanceStartResult.SECONDARY
        if self._server.listen(self.server_name):
            return InstanceStartResult.PRIMARY

        # A concurrent process may have won the listen race. Retry before
        # treating the endpoint as stale and removing it.
        if self._notify_existing(timeout_ms=500):
            return InstanceStartResult.SECONDARY
        QtNetwork.QLocalServer.removeServer(self.server_name)
        if self._server.listen(self.server_name):
            return InstanceStartResult.PRIMARY
        logger.error("Could not start local server: %s", self._server.errorString())
        return InstanceStartResult.FAILED

    def _notify_existing(self, timeout_ms: int = 250) -> bool:
        socket = QtNetwork.QLocalSocket()
        socket.connectToServer(self.server_name)
        if not socket.waitForConnected(timeout_ms):
            return False
        socket.write(ACTIVATE_COMMAND)
        socket.waitForBytesWritten(timeout_ms)
        socket.disconnectFromServer()
        return True

    @QtCore.Slot()
    def _handle_connections(self) -> None:
        while self._server.hasPendingConnections():
            client = self._server.nextPendingConnection()
            if client is None:
                continue
            self._clients.add(client)
            client.readyRead.connect(lambda client=client: self._read_client(client))
            client.disconnected.connect(lambda client=client: self._remove_client(client))

    def _read_client(self, client: QtNetwork.QLocalSocket) -> None:
        if bytes(client.readAll()) == ACTIVATE_COMMAND:
            self.activation_requested.emit()

    def _remove_client(self, client: QtNetwork.QLocalSocket) -> None:
        self._clients.discard(client)
        client.deleteLater()
