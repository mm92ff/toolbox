from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from app import constants
from app.services.system_utils import get_config_directory
from main import get_app_name


def test_product_name_is_independent_of_executable_filename() -> None:
    with patch("main.sys.argv", ["/tmp/Toolbox-9.9.9-x86_64.AppImage"]):
        assert get_app_name() == constants.PRODUCT_NAME


def test_linux_config_directory_honors_xdg_config_home() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with (
            patch("app.services.system_utils.sys.platform", "linux"),
            patch.dict(os.environ, {"XDG_CONFIG_HOME": temp_dir}, clear=False),
        ):
            config_dir = get_config_directory(constants.CONFIG_DIRECTORY_NAME)

        expected = Path(temp_dir) / constants.CONFIG_DIRECTORY_NAME
        assert config_dir == expected
        assert config_dir.is_dir()


def test_empty_config_name_uses_stable_fallback() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with (
            patch("app.services.system_utils.sys.platform", "linux"),
            patch.dict(os.environ, {"XDG_CONFIG_HOME": temp_dir}, clear=False),
        ):
            config_dir = get_config_directory("")

        assert config_dir.name == constants.CONFIG_DIRECTORY_NAME
