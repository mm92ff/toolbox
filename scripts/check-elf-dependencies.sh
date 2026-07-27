#!/bin/sh
set -eu

TARGET=${1:-}
if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
    echo "ERROR: ELF dependency target directory is missing: $TARGET" >&2
    exit 1
fi

MISSING_REPORT=$(
    find "$TARGET" -type f -exec sh -c '
        for FILE do
            if file -b "$FILE" | grep -q "^ELF "; then
                MISSING=$(ldd "$FILE" 2>/dev/null | grep "not found" || true)
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
