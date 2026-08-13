from __future__ import annotations

import re
from pathlib import Path

from app import constants


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_release_version_is_consistent_across_linux_metadata() -> None:
    version = constants.VERSION
    assert version == "0.45-beta"

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    appdata = (PROJECT_ROOT / "packaging/linux/io.github.toolbox.Toolbox.appdata.xml").read_text(
        encoding="utf-8"
    )
    verifier = (PROJECT_ROOT / "scripts/verify-linux-release.sh").read_text(encoding="utf-8")

    assert f"Version: `{version}`" in readme
    assert f"Toolbox-{version}-x86_64.AppImage" in readme
    assert f'<release version="{version}"' in appdata
    assert f"Toolbox-{version}-x86_64.AppImage" in verifier


def test_current_docs_do_not_reference_an_older_build_filename() -> None:
    current_minor = int(constants.VERSION.split(".", 1)[1].split("-", 1)[0])
    current_files = (
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "packaging/README.md",
        PROJECT_ROOT / "scripts/verify-linux-release.sh",
    )
    old_pattern = re.compile(r"Toolbox-0\.(\d+)-beta-(?:x86_64\.AppImage|amd64\.deb)")

    for path in current_files:
        text = path.read_text(encoding="utf-8")
        referenced_minors = {int(value) for value in old_pattern.findall(text)}
        assert referenced_minors <= {current_minor}, path
