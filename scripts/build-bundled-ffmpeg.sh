#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FFMPEG_VERSION=7.0.2
FFMPEG_SOURCE_DATE_EPOCH=1722646525
SOURCE_NAME="ffmpeg-$FFMPEG_VERSION.tar.xz"
SIGNATURE_NAME="$SOURCE_NAME.asc"
SOURCE_URL="https://ffmpeg.org/releases/$SOURCE_NAME"
SIGNATURE_URL="https://ffmpeg.org/releases/$SIGNATURE_NAME"
SOURCE_PIN="$PROJECT_ROOT/packaging/linux/ffmpeg-source-7.0.2.sha256"
BINARY_PIN="$PROJECT_ROOT/packaging/linux/ffmpeg-x86_64.sha256"
RUNTIME_ARCHIVE_PIN="$PROJECT_ROOT/packaging/linux/ffmpeg-runtime-7.0.2.sha256"
CACHE_DIR=${TOOLBOX_FFMPEG_SOURCE_CACHE:-"$PROJECT_ROOT/.bin/ffmpeg-source"}
BINARY_OUTPUT_DIR=${TOOLBOX_FFMPEG_OUTPUT_DIR:-"$PROJECT_ROOT/thirdparty"}
SOURCE_OUTPUT_DIR=${TOOLBOX_FFMPEG_SOURCE_OUTPUT_DIR:-"$PROJECT_ROOT/dist-source"}
BUILD_JOBS=${TOOLBOX_FFMPEG_BUILD_JOBS:-2}
SOURCE_ARCHIVE=${TOOLBOX_FFMPEG_SOURCE_ARCHIVE:-"$CACHE_DIR/$SOURCE_NAME"}
SOURCE_SIGNATURE="$CACHE_DIR/$SIGNATURE_NAME"
TEMP_ROOT=""

for REQUIRED_TOOL in curl gcc make pkg-config sha256sum tar xz; do
    if ! command -v "$REQUIRED_TOOL" >/dev/null 2>&1; then
        echo "ERROR: Required FFmpeg build tool is missing: $REQUIRED_TOOL" >&2
        exit 1
    fi
done
if ! pkg-config --exists zlib; then
    echo "ERROR: zlib development files are missing. Install zlib1g-dev." >&2
    exit 1
fi
case "$BUILD_JOBS" in
    ''|*[!0-9]*|0)
        echo "ERROR: TOOLBOX_FFMPEG_BUILD_JOBS must be a positive integer." >&2
        exit 1
        ;;
esac

cleanup() {
    if [ -n "$TEMP_ROOT" ] && [ -d "$TEMP_ROOT" ]; then
        rm -rf -- "$TEMP_ROOT"
    fi
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$CACHE_DIR" "$BINARY_OUTPUT_DIR" "$SOURCE_OUTPUT_DIR"
if [ ! -f "$SOURCE_ARCHIVE" ]; then
    PARTIAL_ARCHIVE="$CACHE_DIR/$SOURCE_NAME.partial"
    curl --fail --location --silent --show-error \
        --output "$PARTIAL_ARCHIVE" "$SOURCE_URL"
    mv -- "$PARTIAL_ARCHIVE" "$CACHE_DIR/$SOURCE_NAME"
    SOURCE_ARCHIVE="$CACHE_DIR/$SOURCE_NAME"
fi
if [ ! -f "$SOURCE_SIGNATURE" ]; then
    PARTIAL_SIGNATURE="$SOURCE_SIGNATURE.partial"
    curl --fail --location --silent --show-error \
        --output "$PARTIAL_SIGNATURE" "$SIGNATURE_URL"
    mv -- "$PARTIAL_SIGNATURE" "$SOURCE_SIGNATURE"
fi

EXPECTED_SOURCE_SHA256=$(awk '$2 == "ffmpeg-7.0.2.tar.xz" { print $1; exit }' "$SOURCE_PIN")
ACTUAL_SOURCE_SHA256=$(sha256sum "$SOURCE_ARCHIVE" | awk '{ print $1 }')
if [ -z "$EXPECTED_SOURCE_SHA256" ] || [ "$ACTUAL_SOURCE_SHA256" != "$EXPECTED_SOURCE_SHA256" ]; then
    echo "ERROR: Official FFmpeg source archive SHA-256 verification failed." >&2
    exit 1
fi

TEMP_ROOT=$(mktemp -d)
tar -xf "$SOURCE_ARCHIVE" -C "$TEMP_ROOT"
SOURCE_DIR="$TEMP_ROOT/ffmpeg-$FFMPEG_VERSION"
if [ ! -x "$SOURCE_DIR/configure" ] || [ ! -f "$SOURCE_DIR/COPYING.LGPLv2.1" ]; then
    echo "ERROR: Verified FFmpeg source archive has unexpected contents." >&2
    exit 1
fi

export LC_ALL=C
export TZ=UTC
export SOURCE_DATE_EPOCH=$FFMPEG_SOURCE_DATE_EPOCH
(
    cd "$SOURCE_DIR"
    ./configure \
        --prefix=/usr \
        --disable-debug \
        --disable-doc \
        --disable-network \
        --disable-autodetect \
        --enable-zlib \
        --disable-iconv \
        --disable-bzlib \
        --disable-lzma \
        --disable-sdl2 \
        --disable-xlib \
        --disable-libxcb \
        --disable-vaapi \
        --disable-vdpau \
        --disable-vulkan \
        --disable-opencl \
        --disable-cuda-llvm \
        --disable-cuvid \
        --disable-nvenc \
        --disable-nvdec \
        --disable-ffplay \
        --disable-x86asm \
        --enable-static \
        --disable-shared \
        --disable-gpl \
        --disable-nonfree
    make -j"$BUILD_JOBS" ffmpeg ffprobe
)

LICENSE_REPORT=$($SOURCE_DIR/ffmpeg -L 2>&1)
printf '%s\n' "$LICENSE_REPORT" | grep -F "GNU Lesser General Public" >/dev/null
printf '%s\n' "$LICENSE_REPORT" | grep -F -- "--disable-gpl" >/dev/null
printf '%s\n' "$LICENSE_REPORT" | grep -F -- "--disable-nonfree" >/dev/null
if printf '%s\n' "$LICENSE_REPORT" | grep -F "GNU General Public License" >/dev/null; then
    echo "ERROR: Bundled FFmpeg unexpectedly reports the GPL instead of the LGPL." >&2
    exit 1
fi

PROBE_VIDEO="$TEMP_ROOT/probe.mp4"
PROBE_IMAGE="$TEMP_ROOT/probe.png"
$SOURCE_DIR/ffmpeg -hide_banner -loglevel error \
    -f lavfi -i testsrc=size=320x180:rate=5 -t 1 -c:v mpeg4 -y "$PROBE_VIDEO"
$SOURCE_DIR/ffmpeg -hide_banner -loglevel error \
    -ss 0.2 -i "$PROBE_VIDEO" -frames:v 1 -f image2pipe -vcodec png - \
    >"$PROBE_IMAGE"
if [ ! -s "$PROBE_IMAGE" ]; then
    echo "ERROR: Rebuilt FFmpeg did not produce the thumbnail probe." >&2
    exit 1
fi
$SOURCE_DIR/ffprobe -v error -show_entries format=duration \
    -of default=nw=1 "$PROBE_VIDEO" | grep -F "duration=" >/dev/null

for MEDIA_BINARY in ffmpeg ffprobe; do
    install -m755 "$SOURCE_DIR/$MEDIA_BINARY" "$TEMP_ROOT/$MEDIA_BINARY"
done
ACTUAL_BINARY_HASHES=$(cd "$TEMP_ROOT" && sha256sum ffmpeg ffprobe)
if [ "${TOOLBOX_SKIP_FFMPEG_PIN_CHECK:-0}" != "1" ]; then
    (cd "$TEMP_ROOT" && sha256sum -c "$BINARY_PIN" >/dev/null 2>&1) || {
        echo "ERROR: Rebuilt FFmpeg hashes do not match the reviewed binary pin." >&2
        printf '%s\n' "$ACTUAL_BINARY_HASHES" >&2
        exit 1
    }
fi
install -m755 "$TEMP_ROOT/ffmpeg" "$BINARY_OUTPUT_DIR/ffmpeg"
install -m755 "$TEMP_ROOT/ffprobe" "$BINARY_OUTPUT_DIR/ffprobe"

TOOLBOX_VERSION=$(
    PYTHONPATH="$PROJECT_ROOT" python3 -c \
        'from app.constants import VERSION; print(VERSION)'
)
SOURCE_BUNDLE_BASENAME="Toolbox-$TOOLBOX_VERSION-ffmpeg-$FFMPEG_VERSION-source"
SOURCE_BUNDLE_ROOT="$TEMP_ROOT/$SOURCE_BUNDLE_BASENAME"
mkdir -p "$SOURCE_BUNDLE_ROOT"
install -m644 "$SOURCE_ARCHIVE" "$SOURCE_BUNDLE_ROOT/$SOURCE_NAME"
install -m644 "$SOURCE_SIGNATURE" "$SOURCE_BUNDLE_ROOT/$SIGNATURE_NAME"
install -m644 "$SOURCE_DIR/COPYING.LGPLv2.1" \
    "$SOURCE_BUNDLE_ROOT/COPYING.LGPLv2.1"
install -m644 "$PROJECT_ROOT/packaging/linux/FFMPEG-SOURCE.md" \
    "$SOURCE_BUNDLE_ROOT/README.md"
install -m644 "$SOURCE_PIN" "$SOURCE_BUNDLE_ROOT/ffmpeg-source-7.0.2.sha256"
install -m755 "$PROJECT_ROOT/scripts/build-bundled-ffmpeg.sh" \
    "$SOURCE_BUNDLE_ROOT/build-bundled-ffmpeg.sh"
(
    cd "$SOURCE_BUNDLE_ROOT"
    sha256sum "$SOURCE_NAME" "$SIGNATURE_NAME" COPYING.LGPLv2.1 \
        README.md ffmpeg-source-7.0.2.sha256 build-bundled-ffmpeg.sh \
        > SHA256SUMS
)
SOURCE_BUNDLE="$SOURCE_OUTPUT_DIR/$SOURCE_BUNDLE_BASENAME.tar.xz"
tar --sort=name --mtime="@$FFMPEG_SOURCE_DATE_EPOCH" \
    --owner=0 --group=0 --numeric-owner \
    -C "$TEMP_ROOT" -cJf "$TEMP_ROOT/source-bundle.tar.xz" \
    "$SOURCE_BUNDLE_BASENAME"
mv -- "$TEMP_ROOT/source-bundle.tar.xz" "$SOURCE_BUNDLE"
(
    cd "$SOURCE_OUTPUT_DIR"
    sha256sum "$(basename "$SOURCE_BUNDLE")" \
        >"$(basename "$SOURCE_BUNDLE").sha256"
)

RUNTIME_BUNDLE_BASENAME="Toolbox-$TOOLBOX_VERSION-ffmpeg-$FFMPEG_VERSION-linux-x86_64"
RUNTIME_BUNDLE_ROOT="$TEMP_ROOT/$RUNTIME_BUNDLE_BASENAME"
mkdir -p "$RUNTIME_BUNDLE_ROOT"
install -m755 "$TEMP_ROOT/ffmpeg" "$RUNTIME_BUNDLE_ROOT/ffmpeg"
install -m755 "$TEMP_ROOT/ffprobe" "$RUNTIME_BUNDLE_ROOT/ffprobe"
install -m644 "$SOURCE_DIR/COPYING.LGPLv2.1" \
    "$RUNTIME_BUNDLE_ROOT/COPYING.LGPLv2.1"
install -m644 "$PROJECT_ROOT/packaging/linux/FFMPEG-SOURCE.md" \
    "$RUNTIME_BUNDLE_ROOT/README.md"
RUNTIME_BUNDLE="$SOURCE_OUTPUT_DIR/$RUNTIME_BUNDLE_BASENAME.tar.xz"
tar --sort=name --mtime="@$FFMPEG_SOURCE_DATE_EPOCH" \
    --owner=0 --group=0 --numeric-owner \
    -C "$TEMP_ROOT" -cJf "$TEMP_ROOT/runtime-bundle.tar.xz" \
    "$RUNTIME_BUNDLE_BASENAME"
ACTUAL_RUNTIME_BUNDLE_SHA256=$(sha256sum "$TEMP_ROOT/runtime-bundle.tar.xz" | awk '{ print $1 }')
if [ "${TOOLBOX_SKIP_FFMPEG_RUNTIME_PIN_CHECK:-0}" != "1" ]; then
    EXPECTED_RUNTIME_BUNDLE_SHA256=$(awk 'NF { print $1; exit }' "$RUNTIME_ARCHIVE_PIN")
    if [ "$ACTUAL_RUNTIME_BUNDLE_SHA256" != "$EXPECTED_RUNTIME_BUNDLE_SHA256" ]; then
        echo "ERROR: Rebuilt FFmpeg runtime archive does not match the reviewed pin." >&2
        echo "$ACTUAL_RUNTIME_BUNDLE_SHA256  $(basename "$RUNTIME_BUNDLE")" >&2
        exit 1
    fi
fi
mv -- "$TEMP_ROOT/runtime-bundle.tar.xz" "$RUNTIME_BUNDLE"
(
    cd "$SOURCE_OUTPUT_DIR"
    sha256sum "$(basename "$RUNTIME_BUNDLE")" \
        >"$(basename "$RUNTIME_BUNDLE").sha256"
)

printf '%s\n' "$ACTUAL_BINARY_HASHES"
echo "$ACTUAL_RUNTIME_BUNDLE_SHA256  $(basename "$RUNTIME_BUNDLE")"
echo "Runtime archive: $RUNTIME_BUNDLE"
echo "Runtime archive checksum: $RUNTIME_BUNDLE.sha256"
echo "Corresponding source: $SOURCE_BUNDLE"
echo "Corresponding source checksum: $SOURCE_BUNDLE.sha256"
