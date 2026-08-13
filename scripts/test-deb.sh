#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEB=${1:-}
if [ -z "$DEB" ] || [ ! -f "$DEB" ]; then
    echo "ERROR: DEB package was not found: $DEB" >&2
    exit 1
fi
DEB=$(
    CDPATH= cd -- "$(dirname -- "$DEB")" \
        && printf '%s/%s\n' "$PWD" "$(basename -- "$DEB")"
)

TEST_ROOT=$(mktemp -d)
PACKAGE_ROOT="$TEST_ROOT/package"
CONTROL_ROOT="$TEST_ROOT/control"
CONFIG_ROOT="$TEST_ROOT/config"
REPORT="$TEST_ROOT/smoke.json"
cleanup() {
    chmod -R u+w "$TEST_ROOT" 2>/dev/null || true
    rm -rf -- "$TEST_ROOT"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$PACKAGE_ROOT" "$CONTROL_ROOT" "$CONFIG_ROOT"
dpkg-deb --extract "$DEB" "$PACKAGE_ROOT"
dpkg-deb --control "$DEB" "$CONTROL_ROOT"

if [ "$(dpkg-deb --field "$DEB" Package)" != "toolbox-launcher" ]; then
    echo "ERROR: Unexpected Debian package name." >&2
    exit 1
fi
if [ "$(dpkg-deb --field "$DEB" Architecture)" != "amd64" ]; then
    echo "ERROR: Unexpected Debian package architecture." >&2
    exit 1
fi
if dpkg-deb --field "$DEB" Depends | grep -q 'libfuse'; then
    echo "ERROR: Native DEB must not require the AppImage FUSE runtime." >&2
    exit 1
fi

for REQUIRED_PATH in \
    usr/bin/toolbox \
    usr/lib/toolbox/toolbox \
    usr/lib/toolbox/_internal/ffmpeg \
    usr/lib/toolbox/_internal/ffprobe \
    usr/lib/toolbox/_internal/libxcb-cursor.so.0 \
    usr/lib/toolbox/_internal/libxkbcommon-x11.so.0 \
    usr/share/applications/io.github.toolbox.Toolbox.desktop \
    usr/share/icons/hicolor/1024x1024/apps/toolbox.png \
    usr/share/metainfo/io.github.toolbox.Toolbox.appdata.xml \
    usr/share/doc/toolbox-launcher/LICENSE \
    usr/share/doc/toolbox-launcher/NOTICE \
    usr/share/doc/toolbox-launcher/THIRD_PARTY_NOTICES.md \
    usr/share/doc/toolbox-launcher/FFMPEG-SOURCE.md \
    usr/share/doc/toolbox-launcher/licenses/FFMPEG-LGPL-2.1.txt \
    usr/share/doc/toolbox-launcher/licenses/XCB-LICENSE.txt \
    usr/share/doc/toolbox-launcher/licenses/XKBCOMMON-LICENSE.txt
do
    if [ ! -e "$PACKAGE_ROOT/$REQUIRED_PATH" ]; then
        echo "ERROR: Required DEB content is missing: $REQUIRED_PATH" >&2
        exit 1
    fi
done

if [ -e "$PACKAGE_ROOT/usr/bin/ffmpeg" ] || [ -e "$PACKAGE_ROOT/usr/bin/ffprobe" ]; then
    echo "ERROR: Bundled media helpers must not replace distro binaries." >&2
    exit 1
fi
if find "$PACKAGE_ROOT/usr/lib/toolbox" -type f -name 'libc.so*' -print -quit | grep -q .; then
    echo "ERROR: glibc must not be bundled in the DEB payload." >&2
    exit 1
fi
if find "$PACKAGE_ROOT" \
    \( -type d \( -name .venv -o -name .pytest_cache -o -name __pycache__ \) \
    -o -type f \( -name '*.AppImage' -o -name '*.bat' -o -name '*.log' \) \) \
    -print -quit | grep -q .; then
    echo "ERROR: Development or AppImage content leaked into the DEB." >&2
    exit 1
fi

desktop-file-validate \
    "$PACKAGE_ROOT/usr/share/applications/io.github.toolbox.Toolbox.desktop"
appstreamcli validate --no-net \
    "$PACKAGE_ROOT/usr/share/metainfo/io.github.toolbox.Toolbox.appdata.xml"
"$PACKAGE_ROOT/usr/lib/toolbox/_internal/ffmpeg" -version >/dev/null
"$PACKAGE_ROOT/usr/lib/toolbox/_internal/ffprobe" -version >/dev/null
FFMPEG_LICENSE_REPORT=$("$PACKAGE_ROOT/usr/lib/toolbox/_internal/ffmpeg" -L 2>&1)
printf '%s\n' "$FFMPEG_LICENSE_REPORT" | grep -F "GNU Lesser General Public" >/dev/null
printf '%s\n' "$FFMPEG_LICENSE_REPORT" | grep -F -- "--disable-gpl" >/dev/null
printf '%s\n' "$FFMPEG_LICENSE_REPORT" | grep -F -- "--disable-nonfree" >/dev/null
if printf '%s\n' "$FFMPEG_LICENSE_REPORT" | grep -F "GNU General Public License" >/dev/null; then
    echo "ERROR: Bundled FFmpeg reports GPL code instead of the reviewed LGPL build." >&2
    exit 1
fi

env -u PYTHONPATH \
    PATH=/usr/bin:/bin \
    PYTHONNOUSERSITE=1 \
    QT_QPA_PLATFORM=offscreen \
    XDG_CONFIG_HOME="$CONFIG_ROOT" \
    TOOLBOX_SMOKE_REPORT="$REPORT" \
    "$PACKAGE_ROOT/usr/bin/toolbox" --smoke-test "--deb-smoke-token"
grep -F -- '"--deb-smoke-token"' "$REPORT" >/dev/null
grep -F -- '"frozen": true' "$REPORT" >/dev/null
grep -F -- '"application_name": "Toolbox"' "$REPORT" >/dev/null

QXCB_PLUGIN=$(find "$PACKAGE_ROOT/usr/lib/toolbox" -type f \
    -path '*/platforms/libqxcb.so' -print -quit)
BUNDLED_LIBRARY_DIR="$PACKAGE_ROOT/usr/lib/toolbox/_internal"
QXCB_DEPENDENCIES=$(LD_LIBRARY_PATH="$BUNDLED_LIBRARY_DIR" ldd "$QXCB_PLUGIN")
if printf '%s\n' "$QXCB_DEPENDENCIES" | grep -q 'not found'; then
    echo "ERROR: Extracted DEB has unresolved Qt xcb dependencies:" >&2
    printf '%s\n' "$QXCB_DEPENDENCIES" >&2
    exit 1
fi
for LIBRARY in libxcb-cursor.so.0 libxkbcommon-x11.so.0
do
    if ! printf '%s\n' "$QXCB_DEPENDENCIES" | \
        grep "$LIBRARY" | grep -F "$BUNDLED_LIBRARY_DIR/" >/dev/null; then
        echo "ERROR: Extracted DEB did not resolve bundled $LIBRARY." >&2
        exit 1
    fi
done
