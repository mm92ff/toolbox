# Bundled FFmpeg corresponding source

Official Toolbox Linux AppImage and DEB releases bundle `ffmpeg` and `ffprobe`
7.0.2 as separate programs for local video-thumbnail extraction.

The binaries are built from the unmodified official FFmpeg source archive:

- Source: `https://ffmpeg.org/releases/ffmpeg-7.0.2.tar.xz`
- Signature: `https://ffmpeg.org/releases/ffmpeg-7.0.2.tar.xz.asc`
- SHA-256: recorded in `packaging/linux/ffmpeg-source-7.0.2.sha256`
- License: GNU Lesser General Public License 2.1 or later

The release does not use `--enable-gpl` or `--enable-nonfree` and does not link
optional third-party codec libraries. The only non-system FFmpeg code in the
binaries comes from the source archive above. The system C library, math
library, dynamic loader, and zlib remain external system libraries.

## Reproduce the binaries and source offer

On Linux Mint 22.3/Ubuntu 24.04 x86_64, install the build tools and run:

```bash
sudo apt install build-essential curl pkg-config xz-utils zlib1g-dev
./scripts/build-bundled-ffmpeg.sh
```

The script downloads and verifies the pinned official source archive, applies
no patches, builds with the complete recorded configure command, confirms the
resulting LGPL license report, tests real MP4-to-PNG extraction, verifies the
pinned binary hashes, and creates:

```text
thirdparty/ffmpeg
thirdparty/ffprobe
dist-source/Toolbox-0.45-beta-ffmpeg-7.0.2-source.tar.xz
dist-source/Toolbox-0.45-beta-ffmpeg-7.0.2-source.tar.xz.sha256
dist-source/Toolbox-0.45-beta-ffmpeg-7.0.2-linux-x86_64.tar.xz
dist-source/Toolbox-0.45-beta-ffmpeg-7.0.2-linux-x86_64.tar.xz.sha256
```

The source release contains the original source archive and signature, the
license text, these instructions, the pin file, and the exact build script.
Publish the source archive and its checksum next to every AppImage and DEB that
contains the matching binaries.
