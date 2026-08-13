from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_windows_build_requirements_are_exactly_pinned() -> None:
    requirements = (PROJECT_ROOT / "requirements-build-windows.txt").read_text(
        encoding="utf-8"
    )
    lines = [line for line in requirements.splitlines() if line.strip()]

    assert "PySide6==6.11.1" in lines
    assert "pyinstaller==6.21.0" in lines
    assert "pyinstaller-hooks-contrib==2026.6" in lines
    assert "pytest==8.4.2" in lines
    assert "ruff==0.16.2" in lines
    assert all("==" in line for line in lines)


def test_windows_spec_embeds_release_and_runtime_notices() -> None:
    spec = (PROJECT_ROOT / "toolbox_lightweight.spec").read_text(encoding="utf-8")

    assert 'for release_document in ("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md")' in spec
    assert "TOOLBOX_WINDOWS_LICENSE_DIR" in spec
    assert "PYTHON-LICENSE.txt" in spec
    assert "PYINSTALLER-COPYING.txt" in spec
    assert "QT-LGPL-3.0.txt" in spec
    assert "WINDOWS-BUILD-INFO.txt" in spec


def test_windows_release_script_builds_tests_and_checksums_exe() -> None:
    script = (PROJECT_ROOT / "scripts" / "build-windows-release.ps1").read_text(
        encoding="utf-8"
    )

    assert "toolbox_lightweight.spec" in script
    assert "TOOLBOX_WINDOWS_LICENSE_DIR" in script
    assert "--windows-smoke-token" in script
    assert "Start-Process" in script
    assert "Get-FileHash" in script
    assert "Compress-Archive" in script
    assert "FFmpeg bundled: no" in script
    assert "QT-LGPL-3.0.txt" in script
    assert "e3a994d82e644b03a792a930f574002658412f62407f5fee083f2555c5f23118" in script


def test_windows_workflow_uses_pinned_actions_and_exact_python() -> None:
    workflow = (
        PROJECT_ROOT / ".github" / "workflows" / "build-windows-release.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "runs-on: windows-2022" in workflow
    assert 'python-version: "3.11.9"' in workflow
    assert "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803" in workflow
    assert "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1" in workflow
    assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" in workflow
    assert "python -m pytest -q" in workflow
    assert "python -m ruff check ." in workflow
    assert "dist-windows/*.exe.sha256" in workflow
