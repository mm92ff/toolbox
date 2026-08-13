# Packaging

## Linux Mint 22.3 AppImage

The release artifact is one executable `.AppImage` file. PyInstaller creates an
internal `onedir` payload, which is copied into an AppDir and compressed by
`appimagetool`.

Prerequisites:

```bash
sudo apt install python3-venv desktop-file-utils libfuse2t64 \
  build-essential curl pkg-config xz-utils zlib1g-dev
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build-linux.txt
```

Build:

```bash
./scripts/build-bundled-ffmpeg.sh
APPIMAGETOOL=/absolute/path/to/appimagetool ./scripts/build-appimage.sh
```

The FFmpeg step builds reviewed LGPL-2.1-or-later `ffmpeg` and `ffprobe`
binaries from the pinned, unmodified official 7.0.2 source archive. It also
creates the mandatory corresponding-source release and checksum in
`dist-source/`. Publish both source files beside every AppImage and DEB. The
AppImage build fails if the matching source release is absent or invalid.

The selected tool must match
`packaging/linux/appimagetool-x86_64.sha256`. A reviewed tool upgrade can be tested
by setting `TOOLBOX_APPIMAGETOOL_SHA256`; commit the new pinned checksum together
with the upgrade. `SOURCE_DATE_EPOCH` defaults to the current Git commit timestamp
and can be supplied explicitly by CI. `PYTHONHASHSEED=0` stabilizes the ordering of
PyInstaller's standard-library archive.

The build performs:

1. clean PyInstaller `onedir` build;
2. AppDir assembly with preserved symlinks;
3. desktop and AppStream validation;
4. headless AppDir smoke test;
5. ELF dependency scan;
6. AppImage creation;
7. SHA-256 generation;
8. normal and extract-and-run AppImage smoke tests.
9. renamed, space-containing, symlinked, and read-only-directory relocation tests;
10. a real XCB smoke test when the builder has an X11 session;
11. extracted-content checks for development files, glibc, accidental FFmpeg,
    and bundled XCB/XKB runtime resolution;
12. in a live X11 session, native window identity, icon metadata, resizing, clean
    window-manager shutdown, and XDG persistence.
13. a Qt scale-factor-2 startup check for the HiDPI code path.

The PyInstaller warning gate permits only imports that belong to other supported
Python platforms (`winreg`, `_winapi`, Java, VMS, and frozen-import internals).
Any new missing-module warning fails the Linux build and must be reviewed.

FFmpeg is never detected from the builder's `PATH`. Normal official builds use
the reviewed outputs from `scripts/build-bundled-ffmpeg.sh`. Explicit paths are
accepted only for controlled verification of binaries that match the committed
hash pins:

```bash
TOOLBOX_FFMPEG_BINARY=/path/to/ffmpeg \
TOOLBOX_FFPROBE_BINARY=/path/to/ffprobe \
./scripts/build-appimage.sh
```

Any intentional FFmpeg version, source, configure-profile, or binary change must
update the source and binary hash pins, `THIRD_PARTY_NOTICES.md`, the source
bundle, and all release artifacts in one reviewed change.

Final release verification:

```bash
./scripts/verify-linux-release.sh \
  dist-appimage/Toolbox-0.45-beta-x86_64.AppImage
```

The `.sha256` file contains a relative filename and therefore remains usable after
the release files are moved together. The corresponding-source `.sha256` follows
the same rule.

To create the native Mint/Ubuntu package from the same verified payload:

```bash
./scripts/build-deb.sh \
  dist-appimage/Toolbox-0.45-beta-x86_64.AppImage
```

The DEB acceptance test extracts the package without root access, validates its
metadata and desktop integration, runs a frozen smoke test, verifies private
FFmpeg placement, and confirms bundled XCB/XKB resolution. Installing the DEB
does not require FUSE.

To compare two repeat builds:

```bash
./scripts/compare-appimage-contents.sh first.AppImage second.AppImage
```

The build fixes the PyInstaller hash seed and normalizes every SquashFS file
timestamp to `SOURCE_DATE_EPOCH`. SquashFS creation uses one worker to avoid
nondeterministic parallel block ordering.
Repeat builds with the same sources and toolchain are expected to be bit-identical.
If hashes still differ, the comparison script distinguishes an archive-metadata
difference from an actual payload difference.
