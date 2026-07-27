#!/bin/sh
set -eu

FIRST=${1:-}
SECOND=${2:-}
if [ -z "$FIRST" ] || [ ! -x "$FIRST" ] || [ -z "$SECOND" ] || [ ! -x "$SECOND" ]; then
    echo "ERROR: Two executable AppImages are required." >&2
    exit 1
fi

FIRST=$(
    CDPATH= cd -- "$(dirname -- "$FIRST")" \
        && printf '%s/%s\n' "$PWD" "$(basename -- "$FIRST")"
)
SECOND=$(
    CDPATH= cd -- "$(dirname -- "$SECOND")" \
        && printf '%s/%s\n' "$PWD" "$(basename -- "$SECOND")"
)

COMPARE_ROOT=$(mktemp -d)
trap 'rm -rf "$COMPARE_ROOT"' EXIT HUP INT TERM
mkdir -p "$COMPARE_ROOT/first" "$COMPARE_ROOT/second"

(
    cd "$COMPARE_ROOT/first"
    "$FIRST" --appimage-extract >/dev/null
)
(
    cd "$COMPARE_ROOT/second"
    "$SECOND" --appimage-extract >/dev/null
)

create_manifest() {
    EXTRACTED_ROOT=$1
    MANIFEST=$2
    (
        cd "$EXTRACTED_ROOT/squashfs-root"
        find . -type f -exec sha256sum {} + | LC_ALL=C sort
        find . -type l -printf 'symlink %p -> %l\n' | LC_ALL=C sort
        find . -printf 'mode %m %y %p\n' | LC_ALL=C sort
    ) > "$MANIFEST"
}

create_manifest "$COMPARE_ROOT/first" "$COMPARE_ROOT/first.manifest"
create_manifest "$COMPARE_ROOT/second" "$COMPARE_ROOT/second.manifest"

if ! cmp -s "$COMPARE_ROOT/first.manifest" "$COMPARE_ROOT/second.manifest"; then
    echo "ERROR: Extracted AppImage contents differ." >&2
    diff -u "$COMPARE_ROOT/first.manifest" "$COMPARE_ROOT/second.manifest" >&2 || true
    exit 1
fi

FIRST_SHA256=$(sha256sum "$FIRST" | awk '{ print $1 }')
SECOND_SHA256=$(sha256sum "$SECOND" | awk '{ print $1 }')
echo "Extracted contents and modes are identical."
if [ "$FIRST_SHA256" = "$SECOND_SHA256" ]; then
    echo "AppImage files are bit-identical: $FIRST_SHA256"
else
    echo "AppImage container hashes differ:"
    echo "  first:  $FIRST_SHA256"
    echo "  second: $SECOND_SHA256"
fi
