#!/bin/sh
set -eu

TARGET=${1:-}
if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
    echo "ERROR: ELF dependency target directory is missing: $TARGET" >&2
    exit 1
fi

BUNDLE_LIBRARY_PATH="$TARGET/_internal"
if [ -d "$TARGET/_internal/PySide6/Qt/lib" ]; then
    BUNDLE_LIBRARY_PATH="$TARGET/_internal/PySide6/Qt/lib:$BUNDLE_LIBRARY_PATH"
fi
if [ -n "${LD_LIBRARY_PATH:-}" ]; then
    BUNDLE_LIBRARY_PATH="$BUNDLE_LIBRARY_PATH:$LD_LIBRARY_PATH"
fi
export BUNDLE_LIBRARY_PATH

MISSING_REPORT=$(
    find "$TARGET" -type f -exec sh -c '
        for FILE do
            if file -b "$FILE" | grep -q "^ELF "; then
                MISSING=$(LD_LIBRARY_PATH="$BUNDLE_LIBRARY_PATH" ldd "$FILE" 2>/dev/null | grep "not found" || true)
                if [ -n "$MISSING" ]; then
                    printf "Missing ELF dependency in %s\n%s\n" "$FILE" "$MISSING"
                fi
            fi
        done
    ' sh {} +
)

if [ -n "$MISSING_REPORT" ]; then
    echo "ERROR: Unresolved ELF dependencies were found:" >&2
    echo "$MISSING_REPORT" >&2
    exit 1
fi
