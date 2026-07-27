#!/bin/sh
set -eu

WARNING_FILE=${1:-}
if [ -z "$WARNING_FILE" ] || [ ! -f "$WARNING_FILE" ]; then
    echo "ERROR: PyInstaller warning file not found: $WARNING_FILE" >&2
    exit 1
fi

UNEXPECTED=$(
    grep -E '^(missing|excluded) module named ' "$WARNING_FILE" \
        | grep -Ev \
            "module named (_winapi|winreg|nt |msvcrt|vms_lib|'java\\.lang'|java |\
_winreg|_wmi|_frozen_importlib_external|_frozen_importlib )" \
        || true
)

if [ -n "$UNEXPECTED" ]; then
    echo "ERROR: Unexpected PyInstaller module warnings were found:" >&2
    echo "$UNEXPECTED" >&2
    exit 1
fi
