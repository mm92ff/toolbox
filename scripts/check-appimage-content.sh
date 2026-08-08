#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APPIMAGE=${1:-}
if [ -z "$APPIMAGE" ] || [ ! -x "$APPIMAGE" ]; then
    echo "ERROR: Executable AppImage not found: $APPIMAGE" >&2
    exit 1
fi
APPIMAGE=$(
    CDPATH= cd -- "$(dirname -- "$APPIMAGE")" \
        && printf '%s/%s\n' "$PWD" "$(basename -- "$APPIMAGE")"
)

EXTRACT_ROOT=$(mktemp -d)
trap 'chmod -R u+w "$EXTRACT_ROOT" 2>/dev/null || true; rm -rf "$EXTRACT_ROOT"' EXIT HUP INT TERM

(
    cd "$EXTRACT_ROOT"
    "$APPIMAGE" --appimage-extract >/dev/null
)

EXTRACTED="$EXTRACT_ROOT/squashfs-root"
for REQUIRED_PATH in \
    AppRun \
    io.github.toolbox.Toolbox.desktop \
    toolbox.png \
    usr/lib/toolbox/toolbox \
    usr/lib/toolbox/_internal/app/assets/one_tray.png \
    usr/share/doc/toolbox/LICENSE \
    usr/share/doc/toolbox/THIRD_PARTY_NOTICES.md \
    usr/share/doc/toolbox/licenses/APPIMAGE-RUNTIME-LICENSE.txt \
    usr/share/doc/toolbox/licenses/ICU-LICENSE.txt \
    usr/share/doc/toolbox/licenses/XCB-LICENSE.txt \
    usr/share/doc/toolbox/licenses/XKBCOMMON-LICENSE.txt \
    usr/share/doc/toolbox/licenses/PYTHON-LICENSE.txt \
    usr/share/doc/toolbox/licenses/PYINSTALLER-COPYING.txt
do
    if [ ! -e "$EXTRACTED/$REQUIRED_PATH" ]; then
        echo "ERROR: Required AppImage content is missing: $REQUIRED_PATH" >&2
        exit 1
    fi
done

if [ ! -x "$EXTRACTED/AppRun" ] || [ ! -x "$EXTRACTED/usr/lib/toolbox/toolbox" ]; then
    echo "ERROR: AppRun or the Toolbox payload is not executable." >&2
    exit 1
fi

FORBIDDEN=$(
    find "$EXTRACTED" \
        \( -type d \( -name .venv -o -name .pytest_cache -o -name __pycache__ \) \
        -o -type f \( -name '*.bat' -o -name '*.log' \) \) \
        -print
)
if [ -n "$FORBIDDEN" ]; then
    echo "ERROR: Forbidden development/build content found in AppImage:" >&2
    echo "$FORBIDDEN" >&2
    exit 1
fi

if [ "${TOOLBOX_EXPECT_BUNDLED_FFMPEG:-0}" = "1" ]; then
    if [ ! -x "$EXTRACTED/usr/bin/ffmpeg" ] || [ ! -x "$EXTRACTED/usr/bin/ffprobe" ]; then
        echo "ERROR: Expected executable FFmpeg/FFprobe payload is missing." >&2
        exit 1
    fi
    "$EXTRACTED/usr/bin/ffmpeg" -version >/dev/null
    "$EXTRACTED/usr/bin/ffprobe" -version >/dev/null
    HASH_FILE="$PROJECT_ROOT/packaging/linux/ffmpeg-x86_64.sha256"
    EXPECTED_FFMPEG_SHA256=$(awk '$2 == "ffmpeg" {print $1}' "$HASH_FILE")
    EXPECTED_FFPROBE_SHA256=$(awk '$2 == "ffprobe" {print $1}' "$HASH_FILE")
    ACTUAL_FFMPEG_SHA256=$(sha256sum "$EXTRACTED/usr/bin/ffmpeg" | awk '{print $1}')
    ACTUAL_FFPROBE_SHA256=$(sha256sum "$EXTRACTED/usr/bin/ffprobe" | awk '{print $1}')
    if [ "$ACTUAL_FFMPEG_SHA256" != "$EXPECTED_FFMPEG_SHA256" ] || \
       [ "$ACTUAL_FFPROBE_SHA256" != "$EXPECTED_FFPROBE_SHA256" ]; then
        echo "ERROR: Bundled FFmpeg/FFprobe checksum does not match the pinned input." >&2
        exit 1
    fi
else
    OPTIONAL_MEDIA_BINARIES=$(
        find "$EXTRACTED/usr/lib/toolbox" -type f \
            \( -name ffmpeg -o -name ffprobe -o -name ffmpeg.exe -o -name ffprobe.exe \) \
            -print
    )
    if [ -n "$OPTIONAL_MEDIA_BINARIES" ]; then
        echo "ERROR: FFmpeg/FFprobe was bundled without an explicit build option." >&2
        echo "$OPTIONAL_MEDIA_BINARIES" >&2
        exit 1
    fi
fi

if find "$EXTRACTED/usr/lib/toolbox" -type f -name 'libc.so*' -print -quit | grep -q .; then
    echo "ERROR: glibc must not be bundled in the AppImage payload." >&2
    exit 1
fi

BUNDLED_LIBRARY_DIR="$EXTRACTED/usr/lib/toolbox/_internal"
QXCB_PLUGIN=$(
    find "$EXTRACTED/usr/lib/toolbox" -type f -path '*/platforms/libqxcb.so' \
        -print -quit
)
if [ -z "$QXCB_PLUGIN" ]; then
    echo "ERROR: Qt xcb platform plugin is missing from the AppImage." >&2
    exit 1
fi
for REQUIRED_LIBRARY in \
    libxcb-cursor.so.0 \
    libxcb-image.so.0 \
    libxcb-render-util.so.0 \
    libxcb-util.so.1 \
    libxcb-xkb.so.1 \
    libxkbcommon.so.0 \
    libxkbcommon-x11.so.0
do
    RESOLVED_LIBRARY=$(
        find "$BUNDLED_LIBRARY_DIR" -maxdepth 1 \
            \( -type f -o -type l \) -name "$REQUIRED_LIBRARY" -print -quit
    )
    if [ -z "$RESOLVED_LIBRARY" ]; then
        echo "ERROR: Required bundled Qt runtime library is missing: $REQUIRED_LIBRARY" >&2
        exit 1
    fi
done

QXCB_DEPENDENCIES=$(LD_LIBRARY_PATH="$BUNDLED_LIBRARY_DIR" ldd "$QXCB_PLUGIN")
if printf '%s\n' "$QXCB_DEPENDENCIES" | grep -q 'not found'; then
    echo "ERROR: Qt xcb plugin still has unresolved runtime dependencies:" >&2
    printf '%s\n' "$QXCB_DEPENDENCIES" >&2
    exit 1
fi
for REQUIRED_LIBRARY in libxcb-cursor.so.0 libxkbcommon-x11.so.0
do
    if ! printf '%s\n' "$QXCB_DEPENDENCIES" | \
        grep "$REQUIRED_LIBRARY" | grep -F "$BUNDLED_LIBRARY_DIR/" >/dev/null; then
        echo "ERROR: Qt xcb plugin did not resolve bundled $REQUIRED_LIBRARY." >&2
        exit 1
    fi
done
