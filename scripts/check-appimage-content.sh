#!/bin/sh
set -eu

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
    usr/share/doc/toolbox/LICENSE \
    usr/share/doc/toolbox/THIRD_PARTY_NOTICES.md \
    usr/share/doc/toolbox/licenses/APPIMAGE-RUNTIME-LICENSE.txt \
    usr/share/doc/toolbox/licenses/ICU-LICENSE.txt \
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

if [ "${TOOLBOX_EXPECT_BUNDLED_FFMPEG:-0}" != "1" ]; then
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
