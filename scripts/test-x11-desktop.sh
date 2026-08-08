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

if [ -z "${DISPLAY:-}" ] || [ "${XDG_SESSION_TYPE:-}" != "x11" ]; then
    echo "SKIP: A live X11 session is required for the desktop-window test."
    exit 0
fi
for REQUIRED_COMMAND in awk cmp find grep sha256sum sleep sort wmctrl xargs xprop xwininfo; do
    if ! command -v "$REQUIRED_COMMAND" >/dev/null 2>&1; then
        if [ "${TOOLBOX_REQUIRE_X11_TEST:-0}" = "1" ]; then
            echo "ERROR: X11 test command is missing: $REQUIRED_COMMAND" >&2
            exit 1
        fi
        echo "SKIP: X11 test command is missing: $REQUIRED_COMMAND"
        exit 0
    fi
done

TEST_ROOT=$(mktemp -d)
TEST_CONFIG="$TEST_ROOT/config"
INSTANCE_KEY="x11-desktop-$$"
RESPONSIVE_REPORT="$TEST_ROOT/responsive-state.json"
APP_PID=
cleanup() {
    if [ -n "$APP_PID" ] && kill -0 "$APP_PID" 2>/dev/null; then
        kill "$APP_PID" 2>/dev/null || true
        wait "$APP_PID" 2>/dev/null || true
    fi
    rm -rf "$TEST_ROOT"
}
trap cleanup EXIT HUP INT TERM

XDG_CONFIG_HOME="$TEST_CONFIG" \
    TOOLBOX_INSTANCE_KEY="$INSTANCE_KEY" \
    TOOLBOX_X11_RESPONSIVE_REPORT="$RESPONSIVE_REPORT" \
    "$APPIMAGE" >"$TEST_ROOT/stdout.log" 2>"$TEST_ROOT/stderr.log" &
APP_PID=$!

WINDOW_ID=
ATTEMPT=0
while [ "$ATTEMPT" -lt 100 ]; do
    WINDOW_ID=$(
        wmctrl -lp | awk -v target="$APP_PID" '$3 == target { print $1; exit }'
    )
    if [ -n "$WINDOW_ID" ]; then
        break
    fi
    if ! kill -0 "$APP_PID" 2>/dev/null; then
        echo "ERROR: Toolbox exited before creating an X11 window." >&2
        cat "$TEST_ROOT/stderr.log" >&2
        exit 1
    fi
    sleep 0.1
    ATTEMPT=$((ATTEMPT + 1))
done
if [ -z "$WINDOW_ID" ]; then
    echo "ERROR: Toolbox X11 window was not found." >&2
    exit 1
fi

WINDOW_LINE=$(wmctrl -lxp | awk -v id="$WINDOW_ID" '$1 == id')
printf '%s\n' "$WINDOW_LINE" | grep -F 'toolbox.Toolbox' >/dev/null
printf '%s\n' "$WINDOW_LINE" | grep -F 'Toolbox' >/dev/null

WINDOW_PROPERTIES=$(xprop -id "$WINDOW_ID" WM_CLASS _NET_WM_NAME _NET_WM_ICON)
printf '%s\n' "$WINDOW_PROPERTIES" | grep -F 'WM_CLASS(STRING) = "toolbox", "Toolbox"' >/dev/null
printf '%s\n' "$WINDOW_PROPERTIES" \
    | grep -F '_NET_WM_NAME(UTF8_STRING) = "Toolbox' >/dev/null
printf '%s\n' "$WINDOW_PROPERTIES" | grep -F '_NET_WM_ICON(CARDINAL)' >/dev/null

read_probe_value() {
    PROBE_KEY=$1
    sed -n "s/.*\"$PROBE_KEY\": \([0-9][0-9]*\).*/\1/p" "$RESPONSIVE_REPORT" \
        2>/dev/null | head -n 1
}

ATTEMPT=0
INITIAL_COLUMNS=
while [ "$ATTEMPT" -lt 100 ]; do
    INITIAL_COLUMNS=$(read_probe_value columns)
    if [ -n "$INITIAL_COLUMNS" ] && [ "$INITIAL_COLUMNS" -gt 1 ]; then
        break
    fi
    sleep 0.1
    ATTEMPT=$((ATTEMPT + 1))
done
if [ -z "$INITIAL_COLUMNS" ] || [ "$INITIAL_COLUMNS" -le 1 ]; then
    echo "ERROR: X11 responsive probe did not start with multiple columns." >&2
    exit 1
fi
grep -F '"canonical_unchanged": true' "$RESPONSIVE_REPORT" >/dev/null
grep -F '"responsive_enabled": true' "$RESPONSIVE_REPORT" >/dev/null

# A second AppImage start must ask the existing process for another window.
find "$TEST_CONFIG" -type f -print0 2>/dev/null \
    | sort -z \
    | xargs -0 -r sha256sum >"$TEST_ROOT/config-before-secondary.sha256"
XDG_CONFIG_HOME="$TEST_CONFIG" \
    TOOLBOX_INSTANCE_KEY="$INSTANCE_KEY" \
    "$APPIMAGE" --new-window >"$TEST_ROOT/secondary.log" 2>&1
find "$TEST_CONFIG" -type f -print0 2>/dev/null \
    | sort -z \
    | xargs -0 -r sha256sum >"$TEST_ROOT/config-after-secondary.sha256"
if ! cmp "$TEST_ROOT/config-before-secondary.sha256" "$TEST_ROOT/config-after-secondary.sha256"; then
    echo "ERROR: Secondary process unexpectedly changed the configuration." >&2
    exit 1
fi
ATTEMPT=0
WINDOW_COUNT=0
while [ "$ATTEMPT" -lt 100 ]; do
    WINDOW_COUNT=$(wmctrl -lp | awk -v target="$APP_PID" '$3 == target { count++ } END { print count + 0 }')
    if [ "$WINDOW_COUNT" -ge 2 ]; then
        break
    fi
    sleep 0.1
    ATTEMPT=$((ATTEMPT + 1))
done
if [ "$WINDOW_COUNT" -ne 2 ]; then
    echo "ERROR: --new-window did not create exactly two windows in the primary PID." >&2
    cat "$TEST_ROOT/secondary.log" >&2
    exit 1
fi

INITIAL_WIDTH=$(xwininfo -id "$WINDOW_ID" | awk '/Width:/ { print $2; exit }')
INITIAL_HEIGHT=$(xwininfo -id "$WINDOW_ID" | awk '/Height:/ { print $2; exit }')
NARROW_WIDTH=220
wmctrl -ir "$WINDOW_ID" -e "0,120,140,$NARROW_WIDTH,$INITIAL_HEIGHT"

ATTEMPT=0
NARROW_COLUMNS=
while [ "$ATTEMPT" -lt 50 ]; do
    CURRENT_WIDTH=$(xwininfo -id "$WINDOW_ID" | awk '/Width:/ { print $2; exit }')
    NARROW_COLUMNS=$(read_probe_value columns)
    if [ "$CURRENT_WIDTH" -le "$NARROW_WIDTH" ] && [ "$NARROW_COLUMNS" = "1" ]; then
        break
    fi
    sleep 0.1
    ATTEMPT=$((ATTEMPT + 1))
done
if [ "$NARROW_COLUMNS" != "1" ]; then
    echo "ERROR: Real X11 narrowing did not produce one responsive column." >&2
    exit 1
fi
grep -F '"canonical_unchanged": true' "$RESPONSIVE_REPORT" >/dev/null

TARGET_WIDTH=$((INITIAL_WIDTH + 120))
TARGET_HEIGHT=$((INITIAL_HEIGHT + 80))
wmctrl -ir "$WINDOW_ID" -e "0,120,140,$TARGET_WIDTH,$TARGET_HEIGHT"

ATTEMPT=0
while [ "$ATTEMPT" -lt 30 ]; do
    CURRENT_WIDTH=$(xwininfo -id "$WINDOW_ID" | awk '/Width:/ { print $2; exit }')
    CURRENT_HEIGHT=$(xwininfo -id "$WINDOW_ID" | awk '/Height:/ { print $2; exit }')
    CURRENT_COLUMNS=$(read_probe_value columns)
    if [ "$CURRENT_WIDTH" -ge "$TARGET_WIDTH" ] \
        && [ "$CURRENT_HEIGHT" -ge "$TARGET_HEIGHT" ] \
        && [ -n "$CURRENT_COLUMNS" ] \
        && [ "$CURRENT_COLUMNS" -gt 1 ]; then
        break
    fi
    sleep 0.1
    ATTEMPT=$((ATTEMPT + 1))
done
if [ "$CURRENT_WIDTH" -lt "$TARGET_WIDTH" ] \
    || [ "$CURRENT_HEIGHT" -lt "$TARGET_HEIGHT" ] \
    || [ -z "$CURRENT_COLUMNS" ] \
    || [ "$CURRENT_COLUMNS" -le 1 ]; then
    echo "ERROR: Toolbox did not restore multiple columns after X11 expansion." >&2
    exit 1
fi
grep -F '"canonical_unchanged": true' "$RESPONSIVE_REPORT" >/dev/null

wmctrl -lp | awk -v target="$APP_PID" '$3 == target { print $1 }' | while IFS= read -r id; do
    wmctrl -ic "$id"
done
wait "$APP_PID"
APP_PID=

if [ ! -f "$TEST_CONFIG/toolbox/tools.json" ] \
    || [ ! -f "$TEST_CONFIG/toolbox/ui_settings.json" ]; then
    echo "ERROR: Toolbox did not persist state in the XDG configuration directory." >&2
    exit 1
fi
