#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${TOOLBOX_BUILD_PYTHON:-"$PROJECT_ROOT/.venv/bin/python"}
APPIMAGETOOL_BIN=${APPIMAGETOOL:-}
VERSION=${TOOLBOX_VERSION:-}
ARCHITECTURE=${ARCH:-x86_64}
PINNED_APPIMAGETOOL_HASH_FILE="$PROJECT_ROOT/packaging/linux/appimagetool-x86_64.sha256"
PINNED_FFMPEG_HASH_FILE="$PROJECT_ROOT/packaging/linux/ffmpeg-x86_64.sha256"
PINNED_FFMPEG_ARCHIVE_HASH_FILE="$PROJECT_ROOT/packaging/linux/ffmpeg-archive-x86_64.sha256"
SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-}
PYTHONHASHSEED=${PYTHONHASHSEED:-0}

BUILD_DIR="$PROJECT_ROOT/build/toolbox_linux"
DIST_DIR="$PROJECT_ROOT/dist"
APPDIR="$PROJECT_ROOT/Toolbox.AppDir"
OUTPUT_DIR="$PROJECT_ROOT/dist-appimage"
OUTPUT="$OUTPUT_DIR/Toolbox-$VERSION-$ARCHITECTURE.AppImage"

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "ERROR: Required build command was not found: $1" >&2
        exit 1
    fi
}

for REQUIRED_COMMAND in \
    appstreamcli awk basename chmod cmp cp desktop-file-validate env file \
    find grep head install ldd ln mkdir rm sha256sum sort uname
do
    require_command "$REQUIRED_COMMAND"
done

if [ -z "$SOURCE_DATE_EPOCH" ]; then
    if command -v git >/dev/null 2>&1; then
        SOURCE_DATE_EPOCH=$(
            git -C "$PROJECT_ROOT" log -1 --format=%ct 2>/dev/null || true
        )
    fi
    SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-315532800}
fi
export SOURCE_DATE_EPOCH
export PYTHONHASHSEED

if [ "$(uname -m)" != "x86_64" ] || [ "$ARCHITECTURE" != "x86_64" ]; then
    echo "ERROR: This build script currently supports x86_64 only." >&2
    exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
    echo "ERROR: Build Python not found: $PYTHON_BIN" >&2
    echo "Create .venv and install requirements-build-linux.txt first." >&2
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import PyInstaller, PySide6' >/dev/null 2>&1; then
    echo "ERROR: PyInstaller and PySide6 must be installed in the build environment." >&2
    exit 1
fi

if [ -z "$VERSION" ]; then
    VERSION=$(
        PYTHONPATH="$PROJECT_ROOT" "$PYTHON_BIN" -c \
            'from app.constants import VERSION; print(VERSION)'
    )
fi
if ! printf '%s\n' "$VERSION" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._+-]*$'; then
    echo "ERROR: Invalid Toolbox version for AppImage filename: $VERSION" >&2
    exit 1
fi
OUTPUT="$OUTPUT_DIR/Toolbox-$VERSION-$ARCHITECTURE.AppImage"

if [ -z "$APPIMAGETOOL_BIN" ]; then
    if command -v appimagetool >/dev/null 2>&1; then
        APPIMAGETOOL_BIN=$(command -v appimagetool)
    elif [ -x "$HOME/.local/bin/appimagetool" ]; then
        APPIMAGETOOL_BIN="$HOME/.local/bin/appimagetool"
    else
        echo "ERROR: appimagetool was not found." >&2
        exit 1
    fi
fi

if [ ! -x "$APPIMAGETOOL_BIN" ]; then
    echo "ERROR: appimagetool is not executable: $APPIMAGETOOL_BIN" >&2
    exit 1
fi

if [ ! -f "$PINNED_APPIMAGETOOL_HASH_FILE" ]; then
    echo "ERROR: Pinned appimagetool checksum is missing." >&2
    exit 1
fi
EXPECTED_APPIMAGETOOL_SHA256=${TOOLBOX_APPIMAGETOOL_SHA256:-$(
    awk 'NF { print $1; exit }' "$PINNED_APPIMAGETOOL_HASH_FILE"
)}
ACTUAL_APPIMAGETOOL_SHA256=$(
    sha256sum "$APPIMAGETOOL_BIN" | awk '{ print $1 }'
)
if [ "$ACTUAL_APPIMAGETOOL_SHA256" != "$EXPECTED_APPIMAGETOOL_SHA256" ]; then
    echo "ERROR: appimagetool checksum does not match the pinned build input." >&2
    echo "Expected: $EXPECTED_APPIMAGETOOL_SHA256" >&2
    echo "Actual:   $ACTUAL_APPIMAGETOOL_SHA256" >&2
    exit 1
fi

rm -rf "$BUILD_DIR" "$DIST_DIR/toolbox" "$APPDIR"
mkdir -p "$DIST_DIR" "$OUTPUT_DIR"
find "$OUTPUT_DIR" -maxdepth 1 -type f \
    \( -name 'Toolbox-*.AppImage' -o -name 'Toolbox-*.AppImage.sha256' \) \
    -delete

"$PYTHON_BIN" -m PyInstaller \
    --clean \
    --noconfirm \
    --workpath "$BUILD_DIR" \
    --distpath "$DIST_DIR" \
    "$PROJECT_ROOT/toolbox_linux.spec"
"$PROJECT_ROOT/scripts/check-pyinstaller-warnings.sh" \
    "$BUILD_DIR/toolbox_linux/warn-toolbox_linux.txt"

install -Dm755 "$PROJECT_ROOT/packaging/linux/AppRun" "$APPDIR/AppRun"
install -Dm644 \
    "$PROJECT_ROOT/packaging/linux/toolbox.desktop" \
    "$APPDIR/usr/share/applications/io.github.toolbox.Toolbox.desktop"
install -Dm644 \
    "$PROJECT_ROOT/packaging/linux/io.github.toolbox.Toolbox.appdata.xml" \
    "$APPDIR/usr/share/metainfo/io.github.toolbox.Toolbox.appdata.xml"
install -Dm644 \
    "$PROJECT_ROOT/app/assets/one.png" \
    "$APPDIR/usr/share/icons/hicolor/1024x1024/apps/toolbox.png"
install -Dm644 "$PROJECT_ROOT/LICENSE" "$APPDIR/usr/share/doc/toolbox/LICENSE"
install -Dm644 \
    "$PROJECT_ROOT/THIRD_PARTY_NOTICES.md" \
    "$APPDIR/usr/share/doc/toolbox/THIRD_PARTY_NOTICES.md"
install -Dm644 \
    "$PROJECT_ROOT/packaging/linux/licenses/APPIMAGE-RUNTIME-LICENSE.txt" \
    "$APPDIR/usr/share/doc/toolbox/licenses/APPIMAGE-RUNTIME-LICENSE.txt"
install -Dm644 \
    "$PROJECT_ROOT/packaging/linux/licenses/ICU-LICENSE.txt" \
    "$APPDIR/usr/share/doc/toolbox/licenses/ICU-LICENSE.txt"

PYTHON_LICENSE=$(
    "$PYTHON_BIN" -c '
import sys
import sysconfig
from pathlib import Path

version = f"{sys.version_info.major}.{sys.version_info.minor}"
candidates = (
    Path(sys.base_prefix) / "LICENSE.txt",
    Path(sysconfig.get_path("stdlib")) / "LICENSE.txt",
    Path("/usr/share/doc") / f"python{version}" / "copyright",
)
for candidate in candidates:
    if candidate.is_file():
        print(candidate)
        break
else:
    raise SystemExit("Python license file was not found")
'
)
install -Dm644 \
    "$PYTHON_LICENSE" \
    "$APPDIR/usr/share/doc/toolbox/licenses/PYTHON-LICENSE.txt"

PYINSTALLER_LICENSE=$(
    "$PYTHON_BIN" -c \
        'from importlib.metadata import distribution; d=distribution("pyinstaller"); p=next(p for p in d.files if str(p).endswith("licenses/COPYING.txt")); print(d.locate_file(p))'
)
install -Dm644 \
    "$PYINSTALLER_LICENSE" \
    "$APPDIR/usr/share/doc/toolbox/licenses/PYINSTALLER-COPYING.txt"
install -Dm644 \
    /usr/share/common-licenses/LGPL-3 \
    "$APPDIR/usr/share/doc/toolbox/licenses/LGPL-3.txt"
install -Dm644 \
    /usr/share/common-licenses/GPL-3 \
    "$APPDIR/usr/share/doc/toolbox/licenses/GPL-3.txt"

{
    echo "Toolbox version: $VERSION"
    echo "Architecture: $ARCHITECTURE"
    echo "SOURCE_DATE_EPOCH: $SOURCE_DATE_EPOCH"
    echo "PYTHONHASHSEED: $PYTHONHASHSEED"
    uname -a
    ldd --version | head -n 1
    "$PYTHON_BIN" --version
    "$PYTHON_BIN" -m PyInstaller --version
    "$PYTHON_BIN" -c \
        'import PySide6; print("PySide6", PySide6.__version__)'
    "$APPIMAGETOOL_BIN" --version 2>&1 | head -n 1
    echo "appimagetool SHA-256: $ACTUAL_APPIMAGETOOL_SHA256"
} > "$APPDIR/usr/share/doc/toolbox/build-info.txt"

mkdir -p "$APPDIR/usr/lib"
cp -a "$DIST_DIR/toolbox" "$APPDIR/usr/lib/toolbox"
mkdir -p "$APPDIR/usr/bin"
ln -s ../lib/toolbox/toolbox "$APPDIR/usr/bin/toolbox"
ln -s \
    usr/share/applications/io.github.toolbox.Toolbox.desktop \
    "$APPDIR/io.github.toolbox.Toolbox.desktop"
ln -s usr/share/icons/hicolor/1024x1024/apps/toolbox.png "$APPDIR/toolbox.png"

# Bundle only locally supplied, pinned FFmpeg binaries. Network downloads are
# deliberately excluded from the release build so identical inputs stay reproducible.
FFMPEG_SOURCE=${TOOLBOX_FFMPEG_BINARY:-}
FFPROBE_SOURCE=${TOOLBOX_FFPROBE_BINARY:-}
if [ -z "$FFMPEG_SOURCE" ] || [ -z "$FFPROBE_SOURCE" ]; then
    if [ -x "$PROJECT_ROOT/thirdparty/ffmpeg" ] && [ -x "$PROJECT_ROOT/thirdparty/ffprobe" ]; then
        FFMPEG_SOURCE="$PROJECT_ROOT/thirdparty/ffmpeg"
        FFPROBE_SOURCE="$PROJECT_ROOT/thirdparty/ffprobe"
    elif [ -x "$PROJECT_ROOT/.bin/ffmpeg" ] && [ -x "$PROJECT_ROOT/.bin/ffprobe" ]; then
        FFMPEG_SOURCE="$PROJECT_ROOT/.bin/ffmpeg"
        FFPROBE_SOURCE="$PROJECT_ROOT/.bin/ffprobe"
    else
        echo "ERROR: Verified FFmpeg/FFprobe inputs are required for an AppImage build." >&2
        exit 1
    fi
fi
EXPECTED_FFMPEG_SHA256=$(awk '$2 == "ffmpeg" {print $1}' "$PINNED_FFMPEG_HASH_FILE")
EXPECTED_FFPROBE_SHA256=$(awk '$2 == "ffprobe" {print $1}' "$PINNED_FFMPEG_HASH_FILE")
EXPECTED_FFMPEG_ARCHIVE_SHA256=$(awk 'NF {print $1; exit}' "$PINNED_FFMPEG_ARCHIVE_HASH_FILE")
ACTUAL_FFMPEG_SHA256=$(sha256sum "$FFMPEG_SOURCE" | awk '{print $1}')
ACTUAL_FFPROBE_SHA256=$(sha256sum "$FFPROBE_SOURCE" | awk '{print $1}')
if [ "$ACTUAL_FFMPEG_SHA256" != "$EXPECTED_FFMPEG_SHA256" ] || \
   [ "$ACTUAL_FFPROBE_SHA256" != "$EXPECTED_FFPROBE_SHA256" ]; then
    echo "ERROR: FFmpeg input SHA-256 verification failed." >&2
    exit 1
fi
cp "$FFMPEG_SOURCE" "$APPDIR/usr/bin/ffmpeg"
cp "$FFPROBE_SOURCE" "$APPDIR/usr/bin/ffprobe"
chmod +x "$APPDIR/usr/bin/ffmpeg" "$APPDIR/usr/bin/ffprobe"
{
    echo "FFmpeg version: 7.0.2-static"
    echo "FFmpeg source: https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    echo "FFmpeg source archive SHA-256: $EXPECTED_FFMPEG_ARCHIVE_SHA256"
    echo "FFmpeg SHA-256: $ACTUAL_FFMPEG_SHA256"
    echo "FFprobe SHA-256: $ACTUAL_FFPROBE_SHA256"
} >> "$APPDIR/usr/share/doc/toolbox/build-info.txt"

desktop-file-validate \
    "$APPDIR/usr/share/applications/io.github.toolbox.Toolbox.desktop"
appstreamcli validate --no-net \
    "$APPDIR/usr/share/metainfo/io.github.toolbox.Toolbox.appdata.xml"
"$PROJECT_ROOT/scripts/test-appdir.sh" "$APPDIR"
"$PROJECT_ROOT/scripts/check-elf-dependencies.sh" "$APPDIR/usr/lib/toolbox"

# Metadata is validated locally above. Avoid appimagetool's additional network
# validation so the build remains reproducible when DNS or GitHub is unavailable.
# This pinned appimagetool passes its own SquashFS timestamp flag, which conflicts
# with mksquashfs' SOURCE_DATE_EPOCH handling.
env -u SOURCE_DATE_EPOCH \
    ARCH="$ARCHITECTURE" \
    "$APPIMAGETOOL_BIN" \
    --no-appstream \
    --mksquashfs-opt=-processors \
    --mksquashfs-opt=1 \
    --mksquashfs-opt=-all-time \
    --mksquashfs-opt="$SOURCE_DATE_EPOCH" \
    "$APPDIR" \
    "$OUTPUT"
chmod +x "$OUTPUT"
(
    cd "$OUTPUT_DIR"
    sha256sum "$(basename "$OUTPUT")" > "$(basename "$OUTPUT").sha256"
)
TOOLBOX_EXPECT_BUNDLED_FFMPEG=1 \
    "$PROJECT_ROOT/scripts/check-appimage-content.sh" "$OUTPUT"
"$PROJECT_ROOT/scripts/test-appimage.sh" "$OUTPUT"
if [ -n "${DISPLAY:-}" ] && [ "${XDG_SESSION_TYPE:-}" = "x11" ]; then
    TOOLBOX_REQUIRE_X11_TEST=1 \
        "$PROJECT_ROOT/scripts/test-x11-desktop.sh" "$OUTPUT"
fi

echo "AppImage: $OUTPUT"
echo "Checksum: $OUTPUT.sha256"
