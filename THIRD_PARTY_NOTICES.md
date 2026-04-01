# Third-Party Notices

This project includes or supports third-party components.

## FFmpeg / FFprobe

- Component: `ffmpeg`, `ffprobe`
- Upstream project: https://ffmpeg.org/
- Copyright: FFmpeg developers
- License: GNU General Public License (GPL) v3 or later (for the bundled `full_build` binaries)

### Why this matters

The application can ship FFmpeg/FFprobe binaries for video thumbnail generation.
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
