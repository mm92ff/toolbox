# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path


project_root = Path(globals().get("SPECPATH", os.getcwd())).resolve()
app_icon_png = project_root / "app" / "assets" / "one.png"
datas: list[tuple[str, str]] = []
if app_icon_png.is_file():
    datas.append((str(app_icon_png), "app/assets"))


def _explicit_optional_binary(env_var: str, binary_name: str) -> list[tuple[str, str]]:
    raw_path = os.environ.get(env_var, "").strip()
    if not raw_path:
        return []
    candidate = Path(raw_path).expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(f"{env_var} does not point to a file: {candidate}")
    return [(str(candidate), binary_name)]


binaries = [
    *_explicit_optional_binary("TOOLBOX_FFMPEG_BINARY", "ffmpeg"),
    *_explicit_optional_binary("TOOLBOX_FFPROBE_BINARY", "ffprobe"),
]

qt_excludes = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.QtGraphsWidgets",
    "PySide6.QtHttpServer",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth",
    "PySide6.QtNfc",
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
    "PySide6.QtSpatialAudio",
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
]

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[str(project_root / "packaging" / "pyinstaller-hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=qt_excludes,
    noarchive=False,
    optimize=1,
)
# Linux Mint 22.3 is the oldest supported target. Use its base-system
# libraries instead of copying them from the builder; the Python, PySide6,
# Qt, Shiboken, and ICU files installed outside /lib and /usr/lib remain
# bundled.
a.exclude_system_libraries()

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="toolbox",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="toolbox",
)
