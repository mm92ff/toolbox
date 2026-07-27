# Packaging

## Linux Mint 22.3 AppImage

The release artifact is one executable `.AppImage` file. PyInstaller creates an
internal `onedir` payload, which is copied into an AppDir and compressed by
`appimagetool`.

Prerequisites:

```bash
sudo apt install python3-venv desktop-file-utils libfuse2t64
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build-linux.txt
```

Build:

```bash
APPIMAGETOOL=/absolute/path/to/appimagetool ./scripts/build-appimage.sh
```

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
11. extracted-content checks for development files, glibc, and accidental FFmpeg.
12. in a live X11 session, native window identity, icon metadata, resizing, clean
    window-manager shutdown, and XDG persistence.
13. a Qt scale-factor-2 startup check for the HiDPI code path.

The PyInstaller warning gate permits only imports that belong to other supported
Python platforms (`winreg`, `_winapi`, Java, VMS, and frozen-import internals).
Any new missing-module warning fails the Linux build and must be reviewed.

FFmpeg is not detected from the builder's `PATH`. Bundle it only through explicit
absolute paths:

```bash
TOOLBOX_FFMPEG_BINARY=/path/to/ffmpeg \
TOOLBOX_FFPROBE_BINARY=/path/to/ffprobe \
./scripts/build-appimage.sh
```

When FFmpeg is bundled, update `THIRD_PARTY_NOTICES.md` with the exact binary
provenance, license, and corresponding source.

Final release verification:

```bash
./scripts/verify-linux-release.sh \
  dist-appimage/Toolbox-0.42-beta-x86_64.AppImage
```

The `.sha256` file contains a relative filename and therefore remains usable after
the two release files are moved together.

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
