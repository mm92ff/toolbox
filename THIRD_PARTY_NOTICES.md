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
- Bundled Linux build: Toolbox reproducible build of FFmpeg `7.0.2`
- Official source archive: https://ffmpeg.org/releases/ffmpeg-7.0.2.tar.xz
- Official source signature: https://ffmpeg.org/releases/ffmpeg-7.0.2.tar.xz.asc
- Source archive hash: `packaging/linux/ffmpeg-source-7.0.2.sha256`
- Bundled binary hashes: `packaging/linux/ffmpeg-x86_64.sha256`
- Copyright: FFmpeg developers
- License: GNU Lesser General Public License version 2.1 or later

### Linux release build and separation

Official Toolbox Linux AppImage and DEB releases contain FFmpeg and FFprobe as
separate executables used through command-line arguments for local video-thumbnail
generation. They are not linked into the MIT-licensed Toolbox application.

The release binaries are built by `scripts/build-bundled-ffmpeg.sh` from the
unmodified official source archive. The fixed configure profile explicitly uses
`--disable-gpl`, `--disable-nonfree`, and `--disable-autodetect`. It links no
optional third-party codec libraries. The system C library, math library, dynamic
loader, and zlib remain external system libraries.

The build verifies the LGPL report emitted by `ffmpeg -L`, exercises real
MP4-to-PNG thumbnail extraction, and checks both binaries against their reviewed
SHA-256 values before Linux packaging proceeds.

### Corresponding source code

Each Toolbox Linux release that contains these binaries must be accompanied at the
same download location by:

- `Toolbox-0.45-beta-ffmpeg-7.0.2-source.tar.xz`
- `Toolbox-0.45-beta-ffmpeg-7.0.2-source.tar.xz.sha256`

The source release contains the original FFmpeg source archive and upstream
signature, `COPYING.LGPLv2.1`, the exact Toolbox build script and instructions,
and a manifest covering every included file. See
`packaging/linux/FFMPEG-SOURCE.md` for reproduction instructions.

The AppImage builder refuses to create an official release unless that matching
source release exists and passes its checksum. The DEB is derived from the same
verified AppImage payload.

Source runs can install the same reviewed LGPL binaries from the matching
`Toolbox-0.45-beta-ffmpeg-7.0.2-linux-x86_64.tar.xz` release asset. That runtime
archive includes the LGPL text and source instructions, and its SHA-256 is pinned
in both the application and `packaging/linux/ffmpeg-runtime-7.0.2.sha256`.

Windows EXE builds do not bundle FFmpeg automatically. If FFmpeg/FFprobe are
explicitly selected for a future Windows distribution, add the exact Windows
binary provenance, applicable license, and matching corresponding-source release
before publishing that artifact.

### License text

- LGPLv2.1 license text: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt
- FFmpeg legal page: https://ffmpeg.org/legal.html

## No Legal Advice

This document is provided for transparency and engineering compliance tracking only, not legal advice.
