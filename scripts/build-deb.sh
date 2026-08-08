#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APPIMAGE=${1:-}
OUTPUT_DIR="$PROJECT_ROOT/dist-deb"
PACKAGE_NAME=toolbox-launcher
ARCHITECTURE=amd64
SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-}

if [ -z "$APPIMAGE" ]; then
    APPIMAGE=$(find "$PROJECT_ROOT/dist-appimage" -maxdepth 1 -type f \
        -name 'Toolbox-*-x86_64.AppImage' -print -quit)
fi
if [ -z "$APPIMAGE" ] || [ ! -x "$APPIMAGE" ]; then
    echo "ERROR: Build and verify the x86_64 AppImage before creating the DEB." >&2
    exit 1
fi
APPIMAGE=$(
    CDPATH= cd -- "$(dirname -- "$APPIMAGE")" \
        && printf '%s/%s\n' "$PWD" "$(basename -- "$APPIMAGE")"
)

for REQUIRED_COMMAND in \
    awk chmod cp dpkg dpkg-deb du find grep mkdir mktemp mv rm sed sha256sum touch
do
    if ! command -v "$REQUIRED_COMMAND" >/dev/null 2>&1; then
        echo "ERROR: Required DEB build command was not found: $REQUIRED_COMMAND" >&2
        exit 1
    fi
done

if [ -z "$SOURCE_DATE_EPOCH" ]; then
    SOURCE_DATE_EPOCH=$(git -C "$PROJECT_ROOT" log -1 --format=%ct 2>/dev/null || true)
    SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-315532800}
fi

VERSION=$(awk -F'"' '/^VERSION = / { print $2; exit }' "$PROJECT_ROOT/app/constants.py")
if [ -z "$VERSION" ]; then
    echo "ERROR: Toolbox version could not be read." >&2
    exit 1
fi
DEBIAN_UPSTREAM_VERSION=$(printf '%s\n' "$VERSION" | sed 's/-/~/g')
DEBIAN_VERSION=${TOOLBOX_DEB_VERSION:-"$DEBIAN_UPSTREAM_VERSION-1"}
if ! dpkg --validate-version "$DEBIAN_VERSION" >/dev/null 2>&1; then
    echo "ERROR: Invalid Debian package version: $DEBIAN_VERSION" >&2
    exit 1
fi

TEMP_ROOT=$(mktemp -d)
EXTRACT_ROOT="$TEMP_ROOT/extracted"
PACKAGE_ROOT="$TEMP_ROOT/package"
CONTROL_ROOT="$PACKAGE_ROOT/DEBIAN"
OUTPUT="$OUTPUT_DIR/Toolbox-$VERSION-$ARCHITECTURE.deb"
cleanup() {
    chmod -R u+w "$TEMP_ROOT" 2>/dev/null || true
    rm -rf -- "$TEMP_ROOT"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$EXTRACT_ROOT" "$CONTROL_ROOT" "$OUTPUT_DIR"
(
    cd "$EXTRACT_ROOT"
    "$APPIMAGE" --appimage-extract >/dev/null
)
APPDIR="$EXTRACT_ROOT/squashfs-root"
BUILD_INFO="$APPDIR/usr/share/doc/toolbox/build-info.txt"
if [ ! -f "$BUILD_INFO" ] || \
   ! grep -F "Toolbox version: $VERSION" "$BUILD_INFO" >/dev/null; then
    echo "ERROR: AppImage payload version does not match project version $VERSION." >&2
    exit 1
fi

mkdir -p "$PACKAGE_ROOT/usr"
cp -a "$APPDIR/usr/." "$PACKAGE_ROOT/usr/"

# The AppImage-private FFmpeg binaries must never shadow distro binaries in
# /usr/bin. PyInstaller exposes _internal as sys._MEIPASS, where Toolbox already
# searches for its bundled media helper.
for MEDIA_BINARY in ffmpeg ffprobe
do
    if [ -e "$PACKAGE_ROOT/usr/bin/$MEDIA_BINARY" ]; then
        mv "$PACKAGE_ROOT/usr/bin/$MEDIA_BINARY" \
            "$PACKAGE_ROOT/usr/lib/toolbox/_internal/$MEDIA_BINARY"
        chmod 0755 "$PACKAGE_ROOT/usr/lib/toolbox/_internal/$MEDIA_BINARY"
    fi
done

if [ -d "$PACKAGE_ROOT/usr/share/doc/toolbox" ]; then
    mv "$PACKAGE_ROOT/usr/share/doc/toolbox" \
        "$PACKAGE_ROOT/usr/share/doc/$PACKAGE_NAME"
fi

INSTALLED_SIZE=$(du -sk "$PACKAGE_ROOT/usr" | awk '{print $1}')
APPIMAGE_SHA256=$(sha256sum "$APPIMAGE" | awk '{print $1}')
cat >"$CONTROL_ROOT/control" <<EOF
Package: $PACKAGE_NAME
Version: $DEBIAN_VERSION
Architecture: $ARCHITECTURE
Maintainer: Toolbox Project <noreply@toolbox.invalid>
Installed-Size: $INSTALLED_SIZE
Section: utils
Priority: optional
Depends: libc6 (>= 2.34), libstdc++6, libgcc-s1, libgl1, libegl1, libfontconfig1, libfreetype6, libglib2.0-0t64, libdbus-1-3, zlib1g, libx11-6, libx11-xcb1, libxcb1, libxcb-icccm4, libxcb-keysyms1, libxcb-randr0, libxcb-render0, libxcb-shape0, libxcb-shm0, libxcb-sync1, libxcb-xfixes0
X-Toolbox-AppImage-SHA256: $APPIMAGE_SHA256
Description: desktop toolbox launcher
 Organize and launch applications, files, folders, desktop entries, and
 AppImages from configurable Toolbox tabs.
EOF
chmod 0644 "$CONTROL_ROOT/control"

find "$PACKAGE_ROOT" -exec touch -h --date="@$SOURCE_DATE_EPOCH" {} +
find "$OUTPUT_DIR" -maxdepth 1 -type f \
    \( -name 'Toolbox-*-amd64.deb' -o -name 'Toolbox-*-amd64.deb.sha256' \) \
    -delete
dpkg-deb --root-owner-group -Zxz -z9 --build "$PACKAGE_ROOT" "$OUTPUT" >/dev/null
(
    cd "$OUTPUT_DIR"
    sha256sum "$(basename "$OUTPUT")" >"$(basename "$OUTPUT").sha256"
)

"$PROJECT_ROOT/scripts/test-deb.sh" "$OUTPUT"
echo "DEB: $OUTPUT"
echo "Checksum: $OUTPUT.sha256"
