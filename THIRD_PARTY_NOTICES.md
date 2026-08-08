# Third-Party Notices

This project includes or supports third-party components.

## Python

- Component: CPython runtime
- Upstream project: https://www.python.org/
- License: Python Software Foundation License

The Linux AppImage contains a Python runtime supplied by the selected build
environment. The matching Python license is copied into the AppImage at build time.

## PySide6 / Qt / Shiboken

- Component: PySide6, Qt 6 libraries and plugins, Shiboken
- Upstream project: https://doc.qt.io/qtforpython-6/
- License options: LGPLv3, GPLv3, or a commercial Qt license

The community AppImage build uses the PyPI community packages. The AppImage includes
the LGPLv3 and GPLv3 license texts and keeps Qt as dynamically linked shared
libraries inside the bundle.

## ICU

- Component: ICU libraries distributed with the PySide6 Qt runtime
- Upstream project: https://icu.unicode.org/
- License: Unicode/ICU license (MIT-style)

The matching ICU license text is included in the AppImage. Linux base-system
libraries are deliberately not copied from the build system.

## PyInstaller

- Component: PyInstaller bootloader and collected runtime support
- Upstream project: https://pyinstaller.org/
- License: GPLv2-or-later with the PyInstaller bootloader exception

The matching PyInstaller license and bootloader exception are copied from the build
environment into the AppImage.

## XCB utility libraries / libxkbcommon

- Components: XCB cursor, image, render-util, util and XKB libraries; libxkbcommon
- Upstream projects: https://xcb.freedesktop.org/ and https://xkbcommon.org/
- License: MIT/X11-style licenses

The Linux AppImage bundles the small XCB/XKB helper libraries required by Qt's
`qxcb` platform plugin. The corresponding license notices are included as
`XCB-LICENSE.txt` and `XKBCOMMON-LICENSE.txt`. glibc and the system graphics
driver stack remain external runtime dependencies.

## AppImage Runtime

- Component: AppImage type-2 runtime and AppDir format
- Upstream project: https://github.com/AppImage/AppImageKit
- License information: https://github.com/AppImage/AppImageKit/blob/master/LICENSE

The AppImage type-2 runtime is MIT-licensed and contains the third-party components
listed in its license notice. That notice is included in the AppImage. The build
validates `appimagetool` against the pinned SHA-256 value before packaging and
records the value in `build-info.txt`.

## FFmpeg / FFprobe

- Component: `ffmpeg`, `ffprobe`
- Upstream project: https://ffmpeg.org/
- Bundled Linux build: `7.0.2-static` from https://johnvansickle.com/ffmpeg/
- Verified source archive: `ffmpeg-release-amd64-static.tar.xz`
- Source archive hash: `packaging/linux/ffmpeg-archive-x86_64.sha256`
- Bundled binary hashes: `packaging/linux/ffmpeg-x86_64.sha256`
- Copyright: FFmpeg developers
- License: GNU General Public License (GPL) v3 or later (for the bundled `full_build` binaries)

### Why this matters

The application can ship FFmpeg/FFprobe binaries for video thumbnail generation,
but Linux AppImage builds do not include them unless explicitly requested.
When these binaries are distributed together with the app, FFmpeg license obligations apply.

### Binary provenance used for current beta builds

- Build flavor: `7.0.2-full_build-www.gyan.dev`
- Distributor/build provider: https://www.gyan.dev/ffmpeg/builds/
- Provider releases: https://github.com/GyanD/codexffmpeg/releases

### Corresponding source code

For the current bundled FFmpeg binary flavor (`7.0.2-full_build-www.gyan.dev`), the provider metadata references:

- FFmpeg source commit: https://github.com/FFmpeg/FFmpeg/commit/e3a61e9103

If you distribute a different FFmpeg binary in future releases, update this file with the matching source reference for that exact binary.

### License text

- GPLv3 license text: https://www.gnu.org/licenses/gpl-3.0.txt
- FFmpeg legal page: https://ffmpeg.org/legal.html

## No Legal Advice

This document is provided for transparency and engineering compliance tracking only, not legal advice.
