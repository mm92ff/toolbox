#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APPDIR=${1:-"$PROJECT_ROOT/Toolbox.AppDir"}

if [ ! -x "$APPDIR/AppRun" ]; then
    echo "ERROR: AppRun is missing or not executable: $APPDIR/AppRun" >&2
    exit 1
fi

if [ -x "$APPDIR/usr/bin/ffmpeg" ] && [ -x "$APPDIR/usr/bin/ffprobe" ]; then
    "$APPDIR/usr/bin/ffmpeg" -version >/dev/null
    "$APPDIR/usr/bin/ffprobe" -version >/dev/null
fi

TEST_ROOT=$(mktemp -d)
TEST_CONFIG="$TEST_ROOT/config"
SMOKE_REPORT="$TEST_ROOT/appdir-smoke.json"
MANIFEST_BEFORE="$TEST_ROOT/appdir-before.sha256"
MANIFEST_AFTER="$TEST_ROOT/appdir-after.sha256"
DESKTOP_FIXTURE="$TEST_ROOT/Frozen Drop.desktop"
DROP_FIXTURE="$TEST_ROOT/input file.txt"
mkdir -p "$TEST_CONFIG"
trap 'rm -rf "$TEST_ROOT"' EXIT HUP INT TERM

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

find "$APPDIR" -type f -exec sha256sum {} + | LC_ALL=C sort > "$MANIFEST_BEFORE"

env -u PYTHONPATH \
    PATH=/usr/bin:/bin \
    PYTHONNOUSERSITE=1 \
    QT_QPA_PLATFORM=offscreen \
    XDG_CONFIG_HOME="$TEST_CONFIG" \
    TOOLBOX_SMOKE_REPORT="$SMOKE_REPORT" \
    TOOLBOX_SMOKE_DESKTOP_ENTRY="$DESKTOP_FIXTURE" \
    TOOLBOX_SMOKE_DROP_PATH="$DROP_FIXTURE" \
    "$APPDIR/AppRun" --smoke-test --appdir-forwarding-token

grep -F -- '"--appdir-forwarding-token"' "$SMOKE_REPORT" >/dev/null
grep -F -- '"application_name": "Toolbox"' "$SMOKE_REPORT" >/dev/null
grep -F -- '"frozen": true' "$SMOKE_REPORT" >/dev/null
grep -F -- '"icon_available": true' "$SMOKE_REPORT" >/dev/null
grep -F -- '"icon_theme_name":' "$SMOKE_REPORT" >/dev/null
grep -F -- '"icon_theme_search_path_count":' "$SMOKE_REPORT" >/dev/null
grep -F -- '"desktop_fixture_field_code": "F"' "$SMOKE_REPORT" >/dev/null
grep -F -- '"desktop_fixture_icon_available": true' "$SMOKE_REPORT" >/dev/null
grep -F -- '"desktop_fixture_mode": "direct"' "$SMOKE_REPORT" >/dev/null
grep -F -- '"desktop_fixture_name": "Eingefrorene Desktop-Probe"' "$SMOKE_REPORT" >/dev/null
grep -F -- "\"$DROP_FIXTURE\"" "$SMOKE_REPORT" >/dev/null
grep -F -- "\"config_directory\": \"$TEST_CONFIG/toolbox\"" "$SMOKE_REPORT" >/dev/null

find "$APPDIR" -type f -exec sha256sum {} + | LC_ALL=C sort > "$MANIFEST_AFTER"
if ! cmp -s "$MANIFEST_BEFORE" "$MANIFEST_AFTER"; then
    echo "ERROR: AppDir contents changed while the application was running." >&2
    exit 1
fi
