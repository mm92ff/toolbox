"""Collect QtGui dependencies while dropping the unusable Linux TIFF plugin."""

from PyInstaller.utils.hooks.qt import add_qt6_dependencies


hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
binaries = [
    entry
    for entry in binaries
    if not entry[0].replace("\\", "/").endswith("/imageformats/libqtiff.so")
]
