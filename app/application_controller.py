#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Application-level single-instance coordination."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from enum import Enum

from PySide6 import QtCore, QtNetwork

from app import constants


logger = logging.getLogger(__name__)
ACTIVATE_COMMAND = b"ACTIVATE"
IPC_VERSION = 1
MAX_IPC_MESSAGE_BYTES = 4096
SUPPORTED_COMMANDS = frozenset({"activate", "new_window"})


def resolve_second_launch_command(
    arguments: list[str] | tuple[str, ...], persisted_action: str
) -> str:
    """Resolve the IPC action, with explicit CLI flags taking precedence."""

    if "--new-window" in arguments:
        return "new_window"
    if "--activate-existing" in arguments:
        return "activate"
    return "new_window" if persisted_action == "new_window" else "activate"


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
    command_received = QtCore.Signal(str, object)

    def __init__(self, server_name: str, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.server_name = server_name
        self._server = QtNetwork.QLocalServer(self)
        self._server.newConnection.connect(self._handle_connections)
        self._clients: set[QtNetwork.QLocalSocket] = set()
        self._buffers: dict[QtNetwork.QLocalSocket, bytearray] = {}

    def start(self, command: str = "activate") -> InstanceStartResult:
        """Start the primary server, or notify the existing primary instance."""

        if self._notify_existing(command=command):
            return InstanceStartResult.SECONDARY
        if self._server.listen(self.server_name):
            return InstanceStartResult.PRIMARY

        # A concurrent process may have won the listen race. Retry before
        # treating the endpoint as stale and removing it.
        if self._notify_existing(timeout_ms=500, command=command):
            return InstanceStartResult.SECONDARY
        QtNetwork.QLocalServer.removeServer(self.server_name)
        if self._server.listen(self.server_name):
            return InstanceStartResult.PRIMARY
        logger.error("Could not start local server: %s", self._server.errorString())
        return InstanceStartResult.FAILED

    @staticmethod
    def encode_command(command: str, payload: object | None = None) -> bytes:
        if command not in SUPPORTED_COMMANDS:
            raise ValueError(f"Unsupported IPC command: {command}")
        message = {"version": IPC_VERSION, "command": command}
        if payload is not None:
            message["payload"] = payload
        encoded = json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
        if len(encoded) > MAX_IPC_MESSAGE_BYTES:
            raise ValueError("IPC message is too large")
        return encoded

    def _notify_existing(
        self, timeout_ms: int = 250, command: str = "activate"
    ) -> bool:
        socket = QtNetwork.QLocalSocket()
        socket.connectToServer(self.server_name)
        if not socket.waitForConnected(timeout_ms):
            return False
        try:
            encoded = self.encode_command(command)
        except ValueError:
            return False
        socket.write(encoded)
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
            self._buffers[client] = bytearray()
            client.readyRead.connect(lambda client=client: self._read_client(client))
            client.disconnected.connect(lambda client=client: self._remove_client(client))

    def _read_client(self, client: QtNetwork.QLocalSocket) -> None:
        buffer = self._buffers.setdefault(client, bytearray())
        buffer.extend(bytes(client.readAll()))
        if len(buffer) > MAX_IPC_MESSAGE_BYTES:
            client.abort()
            return
        if bytes(buffer) == ACTIVATE_COMMAND:
            self._dispatch_command("activate", None)
            buffer.clear()
            return
        while b"\n" in buffer:
            raw, _, remaining = buffer.partition(b"\n")
            buffer[:] = remaining
            if not raw or len(raw) > MAX_IPC_MESSAGE_BYTES:
                continue
            try:
                message = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(message, dict) or message.get("version") != IPC_VERSION:
                continue
            command = message.get("command")
            if not isinstance(command, str) or command not in SUPPORTED_COMMANDS:
                continue
            self._dispatch_command(command, message.get("payload"))

    def _dispatch_command(self, command: str, payload: object) -> None:
        self.command_received.emit(command, payload)
        if command == "activate":
            self.activation_requested.emit()

    def _remove_client(self, client: QtNetwork.QLocalSocket) -> None:
        self._clients.discard(client)
        self._buffers.pop(client, None)
        client.deleteLater()
