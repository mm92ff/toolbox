# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path


# In PyInstaller spec execution, __file__ may be undefined.
project_root = Path(globals().get("SPECPATH", os.getcwd())).resolve()
app_icon_png = project_root / "app" / "assets" / "one.png"
app_icon_ico = project_root / "app" / "assets" / "one.ico"
exe_icon = str(app_icon_ico) if app_icon_ico.is_file() else None
datas: list[tuple[str, str]] = []
if app_icon_png.is_file():
    datas.append((str(app_icon_png), "app/assets"))

for release_document in ("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"):
    document_path = project_root / release_document
    if not document_path.is_file():
        raise FileNotFoundError(f"Required release document is missing: {document_path}")
    datas.append((str(document_path), "."))

windows_license_dir = os.environ.get("TOOLBOX_WINDOWS_LICENSE_DIR", "").strip()
if windows_license_dir:
    license_root = Path(windows_license_dir).expanduser().resolve()
    required_license_files = (
        "PYTHON-LICENSE.txt",
        "PYINSTALLER-COPYING.txt",
        "QT-LGPL-3.0.txt",
        "QT-GPL-3.0.txt",
        "WINDOWS-BUILD-INFO.txt",
    )
    for license_name in required_license_files:
        license_path = license_root / license_name
        if not license_path.is_file():
            raise FileNotFoundError(f"Required Windows license file is missing: {license_path}")
        datas.append((str(license_path), "licenses"))


def _explicit_optional_binary(binary_name: str, env_var: str) -> tuple[str, str] | None:
    env_override = os.environ.get(env_var, "").strip()
    if not env_override:
        return None
    binary_path = Path(env_override).expanduser().resolve()
    if not binary_path.is_file():
        raise FileNotFoundError(f"{env_var} does not point to a file: {binary_path}")
    return (str(binary_path), ".")


def _optional_ffmpeg_binaries() -> list[tuple[str, str]]:
    ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"

    entries: list[tuple[str, str]] = []
    ffmpeg_entry = _explicit_optional_binary(ffmpeg_name, "TOOLBOX_FFMPEG_BINARY")
    if ffmpeg_entry is not None:
        entries.append(ffmpeg_entry)
    ffprobe_entry = _explicit_optional_binary(ffprobe_name, "TOOLBOX_FFPROBE_BINARY")
    if ffprobe_entry is not None:
        entries.append(ffprobe_entry)
    return entries

# Lightweight exclusions: keep QtCore/QtGui/QtWidgets path, strip heavy optional Qt stacks.
qt_excludes = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtWebView",
    "PySide6.QtXml",
    "PySide6.QtXmlPatterns",
]

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=_optional_ffmpeg_binaries(),
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=qt_excludes,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="toolbox_lightweight",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=exe_icon,
)
