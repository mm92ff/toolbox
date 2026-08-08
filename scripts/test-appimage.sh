#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APPIMAGE=${1:-}

if [ -z "$APPIMAGE" ]; then
    APPIMAGE=$(find "$PROJECT_ROOT/dist-appimage" -maxdepth 1 -type f -name '*.AppImage' | head -n 1)
fi
if [ -z "$APPIMAGE" ] || [ ! -x "$APPIMAGE" ]; then
    echo "ERROR: Executable AppImage not found." >&2
    exit 1
fi

TEST_ROOT=$(mktemp -d)
TEST_CONFIG="$TEST_ROOT/config"
TEST_CACHE="$TEST_ROOT/cache"
RELOCATED_DIR="$TEST_ROOT/Download Folder"
RELOCATED_APPIMAGE="$RELOCATED_DIR/Renamed Toolbox.AppImage"
SYMLINKED_APPIMAGE="$TEST_ROOT/Toolbox Link.AppImage"
DESKTOP_FIXTURE="$TEST_ROOT/Frozen Drop.desktop"
DROP_FIXTURE="$TEST_ROOT/input file.txt"
APPIMAGE_ICON_ROOT="$TEST_ROOT/appimage-icon-root"
APPIMAGE_ICON_PAYLOAD="$TEST_ROOT/appimage-icon.squashfs"
APPIMAGE_ICON_FIXTURE="$TEST_ROOT/Static Icon Fixture.AppImage"
FOLDER_APPEARANCE_FIXTURE="$TEST_ROOT/Folder Appearance Fixture"
PRIMARY_CONFIG="$TEST_ROOT/primary-config"
PRIMARY_LOG="$TEST_ROOT/primary.log"
PRIMARY_PID=""
mkdir -p \
    "$TEST_CONFIG" \
    "$TEST_CACHE" \
    "$PRIMARY_CONFIG" \
    "$RELOCATED_DIR" \
    "$APPIMAGE_ICON_ROOT" \
    "$FOLDER_APPEARANCE_FIXTURE"

stop_primary_instance() {
    if [ -n "$PRIMARY_PID" ] && kill -0 "$PRIMARY_PID" 2>/dev/null; then
        kill "$PRIMARY_PID" 2>/dev/null || true
        wait "$PRIMARY_PID" 2>/dev/null || true
    fi
    PRIMARY_PID=""
}

cleanup() {
    stop_primary_instance
    chmod u+w "$RELOCATED_DIR" 2>/dev/null || true
    rm -rf "$TEST_ROOT"
}
trap cleanup EXIT HUP INT TERM

printf '%s\n' \
    '[Desktop Entry]' \
    'Type=Application' \
    'Name=Frozen Desktop Fixture' \
    'Name[de_CH]=Eingefrorene Desktop-Probe' \
    'Exec=/usr/bin/printf %F' \
    'Icon=video-display' \
    'Terminal=false' \
    > "$DESKTOP_FIXTURE"
: > "$DROP_FIXTURE"

if ! command -v mksquashfs >/dev/null 2>&1 || \
   ! command -v unsquashfs >/dev/null 2>&1; then
    echo "ERROR: squashfs-tools are required for the static AppImage icon test." >&2
    exit 1
fi
cp "$PROJECT_ROOT/app/assets/one.png" "$APPIMAGE_ICON_ROOT/fixture.png"
ln -s fixture.png "$APPIMAGE_ICON_ROOT/.DirIcon"
mksquashfs \
    "$APPIMAGE_ICON_ROOT" \
    "$APPIMAGE_ICON_PAYLOAD" \
    -noappend \
    -processors 1 \
    -quiet
cp "$APPIMAGE_ICON_PAYLOAD" "$APPIMAGE_ICON_FIXTURE"
chmod +x "$APPIMAGE_ICON_FIXTURE"

run_smoke_test() {
    TEST_APPIMAGE=$1
    REPORT_PATH=$2
    FORWARD_TOKEN=$3
    shift 3

    env -u PYTHONPATH \
        PATH=/usr/bin:/bin \
        PYTHONNOUSERSITE=1 \
        QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}" \
        XDG_CONFIG_HOME="$TEST_CONFIG" \
        XDG_CACHE_HOME="$TEST_CACHE" \
        TOOLBOX_SMOKE_REPORT="$REPORT_PATH" \
        TOOLBOX_SMOKE_DESKTOP_ENTRY="$DESKTOP_FIXTURE" \
        TOOLBOX_SMOKE_DROP_PATH="$DROP_FIXTURE" \
        TOOLBOX_SMOKE_APPIMAGE_ICON="$APPIMAGE_ICON_FIXTURE" \
        TOOLBOX_SMOKE_FOLDER_APPEARANCE_PATH="${TOOLBOX_SMOKE_FOLDER_APPEARANCE_PATH:-}" \
        TOOLBOX_SMOKE_FOLDER_ICON_SIZE="${TOOLBOX_SMOKE_FOLDER_ICON_SIZE:-}" \
        "$TEST_APPIMAGE" "$@" --smoke-test "$FORWARD_TOKEN"

    grep -F -- "\"$FORWARD_TOKEN\"" "$REPORT_PATH" >/dev/null
    grep -F -- '"application_name": "Toolbox"' "$REPORT_PATH" >/dev/null
    grep -F -- '"desktop_file_name": "io.github.toolbox.Toolbox"' "$REPORT_PATH" >/dev/null
    grep -F -- '"frozen": true' "$REPORT_PATH" >/dev/null
    grep -F -- '"icon_available": true' "$REPORT_PATH" >/dev/null
    grep -F -- '"icon_theme_name":' "$REPORT_PATH" >/dev/null
    grep -F -- '"icon_theme_search_path_count":' "$REPORT_PATH" >/dev/null
    grep -F -- '"folder_icon_size_slider_available": true' "$REPORT_PATH" >/dev/null
    grep -F -- '"folder_icon_size_slider_minimum": 40' "$REPORT_PATH" >/dev/null
    grep -F -- '"folder_icon_size_slider_maximum": 160' "$REPORT_PATH" >/dev/null
    grep -F -- '"folder_icon_size_reset_available": true' "$REPORT_PATH" >/dev/null
    grep -F -- '"desktop_fixture_field_code": "F"' "$REPORT_PATH" >/dev/null
    grep -F -- '"desktop_fixture_icon_available": true' "$REPORT_PATH" >/dev/null
    grep -F -- '"desktop_fixture_mode": "direct"' "$REPORT_PATH" >/dev/null
    grep -F -- '"desktop_fixture_name": "Eingefrorene Desktop-Probe"' "$REPORT_PATH" >/dev/null
    grep -F -- '"appimage_fixture_icon_available": true' "$REPORT_PATH" >/dev/null
    grep -F -- '"appimage_fixture_icon_is_png": true' "$REPORT_PATH" >/dev/null
    grep -F -- "\"$DROP_FIXTURE\"" "$REPORT_PATH" >/dev/null
    # Managed windows append the active toolbox-tab title. Match the stable
    # product-name prefix while still allowing that contextual suffix.
    grep -F -- '"window_title": "Toolbox' "$REPORT_PATH" >/dev/null
    grep -F -- "\"config_directory\": \"$TEST_CONFIG/toolbox\"" "$REPORT_PATH" >/dev/null
}

TOOLBOX_SMOKE_FOLDER_APPEARANCE_PATH="$FOLDER_APPEARANCE_FIXTURE" \
TOOLBOX_SMOKE_FOLDER_ICON_SIZE=118 \
run_smoke_test \
    "$APPIMAGE" \
    "$TEST_ROOT/normal.json" \
    "--normal-forwarding-token"
grep -F -- '"folder_icon_size_browse_visible": true' "$TEST_ROOT/normal.json" >/dev/null
grep -F -- '"folder_icon_size_effective": 118' "$TEST_ROOT/normal.json" >/dev/null
grep -F -- '"folder_icon_size_override": 118' "$TEST_ROOT/normal.json" >/dev/null

TOOLBOX_SMOKE_FOLDER_APPEARANCE_PATH="$FOLDER_APPEARANCE_FIXTURE" \
run_smoke_test \
    "$APPIMAGE" \
    "$TEST_ROOT/folder-appearance-restart.json" \
    "--folder-appearance-restart-token"
grep -F -- '"folder_icon_size_effective": 118' \
    "$TEST_ROOT/folder-appearance-restart.json" >/dev/null
grep -F -- '"folder_icon_size_override": 118' \
    "$TEST_ROOT/folder-appearance-restart.json" >/dev/null

# A smoke run must stay isolated even while the real single-instance server is active.
env -u PYTHONPATH \
    PATH=/usr/bin:/bin \
    PYTHONNOUSERSITE=1 \
    QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}" \
    XDG_CONFIG_HOME="$PRIMARY_CONFIG" \
    TOOLBOX_INSTANCE_KEY="appimage-acceptance-$$" \
    "$APPIMAGE" >"$PRIMARY_LOG" 2>&1 &
PRIMARY_PID=$!
sleep 1
if ! kill -0 "$PRIMARY_PID" 2>/dev/null; then
    cat "$PRIMARY_LOG" >&2
    echo "ERROR: Normal Toolbox instance exited before smoke isolation test." >&2
    exit 1
fi
run_smoke_test \
    "$APPIMAGE" \
    "$TEST_ROOT/running-instance.json" \
    "--running-instance-forwarding-token"
stop_primary_instance

run_smoke_test \
    "$APPIMAGE" \
    "$TEST_ROOT/extract-and-run.json" \
    "--extract-forwarding-token" \
    --appimage-extract-and-run
QT_SCALE_FACTOR=2 run_smoke_test \
    "$APPIMAGE" \
    "$TEST_ROOT/hidpi.json" \
    "--hidpi-forwarding-token"
grep -F -- '"device_pixel_ratio": 2.0' "$TEST_ROOT/hidpi.json" >/dev/null

cp "$APPIMAGE" "$RELOCATED_APPIMAGE"
chmod +x "$RELOCATED_APPIMAGE"
run_smoke_test \
    "$RELOCATED_APPIMAGE" \
    "$TEST_ROOT/renamed.json" \
    "--renamed-forwarding-token"

ln -s "Download Folder/Renamed Toolbox.AppImage" "$SYMLINKED_APPIMAGE"
run_smoke_test \
    "$SYMLINKED_APPIMAGE" \
    "$TEST_ROOT/symlink.json" \
    "--symlink-forwarding-token"

chmod a-w "$RELOCATED_DIR"
run_smoke_test \
    "$RELOCATED_APPIMAGE" \
    "$TEST_ROOT/read-only-directory.json" \
    "--read-only-directory-token"
chmod u+w "$RELOCATED_DIR"

if [ -n "${DISPLAY:-}" ] && [ "${XDG_SESSION_TYPE:-}" = "x11" ]; then
    QT_QPA_PLATFORM=xcb run_smoke_test \
        "$APPIMAGE" \
        "$TEST_ROOT/xcb.json" \
        "--xcb-forwarding-token"
    grep -F -- '"qt_platform": "xcb"' "$TEST_ROOT/xcb.json" >/dev/null
fi
