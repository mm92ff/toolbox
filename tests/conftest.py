from __future__ import annotations

import os
import socket
import urllib.request

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets


@pytest.fixture(scope="session", autouse=True)
def qapp() -> QtWidgets.QApplication:
    """Provide exactly one QApplication for the complete test session."""

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return app


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail normal tests immediately if they attempt an unmocked network request."""

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("External network access is disabled in the test suite.")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
