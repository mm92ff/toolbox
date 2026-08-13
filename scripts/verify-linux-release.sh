#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${TOOLBOX_BUILD_PYTHON:-"$PROJECT_ROOT/.venv/bin/python"}
APPIMAGE=${1:-"$PROJECT_ROOT/dist-appimage/Toolbox-0.45-beta-x86_64.AppImage"}
APPDIR="$PROJECT_ROOT/Toolbox.AppDir"

if [ ! -x "$PYTHON_BIN" ]; then
    echo "ERROR: Test Python not found: $PYTHON_BIN" >&2
    exit 1
fi
if [ ! -x "$APPIMAGE" ]; then
    echo "ERROR: Release AppImage not found or not executable: $APPIMAGE" >&2
    exit 1
fi

QT_QPA_PLATFORM=offscreen "$PYTHON_BIN" -m pytest -q "$PROJECT_ROOT/tests"

desktop-file-validate "$PROJECT_ROOT/packaging/linux/toolbox.desktop"
appstreamcli validate --no-net \
    "$PROJECT_ROOT/packaging/linux/io.github.toolbox.Toolbox.appdata.xml"

CHECKSUM_FILE="$APPIMAGE.sha256"
if [ ! -f "$CHECKSUM_FILE" ]; then
    echo "ERROR: Release checksum is missing: $CHECKSUM_FILE" >&2
    exit 1
fi
(
    cd "$(dirname "$APPIMAGE")"
    sha256sum -c "$(basename "$CHECKSUM_FILE")"
)

TOOLBOX_EXPECT_BUNDLED_FFMPEG=1 \
    "$PROJECT_ROOT/scripts/check-appimage-content.sh" "$APPIMAGE"
"$PROJECT_ROOT/scripts/test-appimage.sh" "$APPIMAGE"
if [ -n "${DISPLAY:-}" ] && [ "${XDG_SESSION_TYPE:-}" = "x11" ]; then
    TOOLBOX_REQUIRE_X11_TEST=1 \
        "$PROJECT_ROOT/scripts/test-x11-desktop.sh" "$APPIMAGE"
fi

if [ -d "$APPDIR/usr/lib/toolbox" ]; then
    "$PROJECT_ROOT/scripts/check-pyinstaller-warnings.sh" \
        "$PROJECT_ROOT/build/toolbox_linux/toolbox_linux/warn-toolbox_linux.txt"
    "$PROJECT_ROOT/scripts/check-elf-dependencies.sh" "$APPDIR/usr/lib/toolbox"
    "$PROJECT_ROOT/scripts/test-appdir.sh" "$APPDIR"
fi

git -C "$PROJECT_ROOT" diff --check
