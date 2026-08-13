# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

## [0.45-beta] - 2026-08-13

### Release preparation

- Synchronized application, AppImage, DEB, documentation, and AppStream
  metadata after the previously tagged `v0.44-beta` still reported `0.42-beta`
- Made the tracked development and code-backup desktop launchers portable by
  resolving their project directory through the desktop-entry `%k` field code
- Replaced the externally built GPL FFmpeg payload with a reproducible
  LGPL-2.1-or-later build from pinned official FFmpeg 7.0.2 source
- Added a mandatory corresponding-source release, third-party notice, exact
  license packaging, and AppImage/DEB compliance checks for bundled FFmpeg
- Documented Windows and Linux release paths and disabled accidental FFmpeg
  collection from the Windows builder's `PATH`

### Added

- Safe multi-window support in one process with shared state, global undo/redo,
  `Ctrl+N`, tab context action, and configurable second-launch behavior
- Application-owned tray menu with Show Last Window, New Window, and Quit
- Versioned, size-limited local IPC commands for activation and new windows
- Linux Mint 22.3 x86_64 AppImage build pipeline with AppDir, desktop metadata,
  AppStream metadata, dependency validation, checksum generation, and smoke tests
- Linux launcher tests for argument handling, working directories, desktop file
  opening, XDG configuration, and PyInstaller environment isolation
- AppImage content, relocation, argument-forwarding, read-only-directory, and
  real-XCB acceptance checks
- `THIRD_PARTY_NOTICES.md` with FFmpeg/FFprobe licensing, provenance, and source-reference guidance for distributed binaries
- New FFmpeg section in Settings with detected source/status, resolved path display, manual path input, browse, and rescan controls
- Windows common-location FFmpeg discovery (Program Files, Chocolatey, Scoop, WinGet package folders)
- Standards-aware Linux desktop-entry parsing for names, icons, `Exec`, `TryExec`,
  working directories, MIME declarations, and freedesktop field codes
- File and URL drops directly onto compatible Linux `.desktop` tiles
- Asynchronous desktop-process monitoring with bounded startup error details
- Browser-style `+` action in the tab bar, with `Ctrl+T`, for creating and
  immediately opening new toolbox tabs
- Toolbox-specific Linux code-backup launcher and verified 7z backup workflow
  with Git-history restoration checks and AppImage/build exclusions
- Optional 8–24 px tile-title font-size slider with automatic icon-size scaling,
  live preview, persistence, and backward-compatible defaults
- Separate system-tray visibility and minimize-on-close settings, with the tray
  icon visible by default for existing profiles
- Per-folder icon-size controls in the folder breadcrumb, including persistent
  overrides, global fallback, reset, and path-local multi-window synchronization
- Responsive wrapping in folder views and an optional width-aware presentation
  for normal toolbox tabs, without modifying saved tile coordinates
- Responsive wrapping is enabled by default for normal toolbox tabs, with a
  one-time migration from the earlier development default
- Bundled XCB cursor/image/utility and XKB runtime helpers for Qt startup on
  Mint systems where the optional host packages are not installed
- Reproducible native `amd64` DEB packaging derived from the verified AppImage
  payload, with dependency metadata, private FFmpeg placement, and smoke tests

### Changed

- Folder views now reflow tiles from multiple columns down to one column as the
  window narrows; responsive normal tabs temporarily disable manual movement
- AppImage content validation now proves that Qt resolves the bundled XCB/XKB
  helpers from the payload and includes their license notices

- Application identity is stable across renamed/versioned executables and honors
  `XDG_CONFIG_HOME` on Linux
- Linux launches restore the host library search path before starting system
  applications, desktop openers, or system FFmpeg
- Linux `wait` launches are reaped by a background waiter instead of blocking the
  Qt GUI thread
- Linux release builds validate a pinned `appimagetool` checksum and create
  portable relative SHA-256 metadata
- Base-system libraries are no longer copied from the Mint builder into the
  AppImage; the release uses the guaranteed Mint 22.3 base system
- Windows-only administrator and window-style controls are hidden on Linux
- README now includes a dedicated third-party licensing section pointing to FFmpeg compliance notes
- FFmpeg resolution order is now: environment override -> manual Settings path -> local/system install (PATH/common locations) -> bundled internal fallback
- Linux desktop tiles now use localized `Name=` metadata and resolve `Icon=`
  through XDG/Cinnamon icon themes before falling back to generic file icons

### Fixed

- Linux builds now package the dedicated tray icon instead of silently falling
  back to the main application image
- AppImage acceptance tests now recognize managed-window titles that include the
  active toolbox tab
- Fresh multi-window profiles now persist their default toolbox state on shutdown

- Executable Linux `.desktop` shortcuts are parsed and launched as safe argument
  arrays instead of being passed directly to the kernel and failing with
  `Exec format error`
- Immediate desktop-launch failures no longer disappear behind a successful GIO
  submission status
- Desktop launch error capture now uses a hard 64 KiB in-memory ring buffer
  instead of retaining unbounded temporary output
- Terminal and D-Bus desktop entries are validated before GIO delegation, and
  delegated file drops no longer show a misleading direct-launch status
- Desktop-tile drag feedback now includes declared MIME compatibility instead
  of deferring that rejection until the drop

## [0.42-beta] - 2026-04-01

### Added

- Keyboard undo/redo support (`Ctrl+Z` / `Ctrl+Y`)
- Context-menu action to add sections from empty canvas space
- Section color manager covering separators from all toolbox tabs
- Bulk and quick-apply controls for all separator line/title colors
- Separate separator spacing controls: `Gap Above` and `Gap Below`
- Help tab content expanded with current behavior and layout rules
- Per-tab background color actions in toolbox context menu (set/reset)
- Image preview thumbnails for supported image files
- Video preview thumbnails for supported video files (ffmpeg-based)
- Preview mode switch: `Fit` or `Fill and crop`
- Hover preview option to show enlarged media thumbnails on mouse-over
- Persistent thumbnail cache with dual variants (`normal` + `HQ`)
- Optional ffmpeg/ffprobe binary bundling support in PyInstaller spec
- Runtime ffmpeg discovery supports bundled binaries and env override (`TOOLBOX_FFMPEG_PATH`)

### Changed

- Refactored settings code into focused modules (`state`, `apply`, `appearance`, `section_colors`, `io`, `profile`)
- Refactored canvas code into focused surface modules (`surface_state`, `surface_render`, `surface_geometry`, `surface_drag`, `surface_interaction`)
- Updated settings persistence to store asymmetric separator spacing while keeping legacy `section_gap` compatibility
- Updated separator layout engine to use asymmetric protected zones (above/below)
- Updated README documentation to reflect current features and behavior
- Help tab text updated to reflect media previews, tab background colors, and current settings behavior

### Fixed

- Multiple multi-select drag issues (horizontal drift, overlap/stacking, structural instability)
- Section drop hint behavior now works consistently in mixed multi-select scenarios
- Inconsistent post-drop spacing behavior near separators
- Broken-entry diagnostics flow hardened to avoid UI hangs by using non-blocking dialog handling
- Icon/layout reflow inconsistencies after icon-size changes in settings
- Hover/preview rendering stability issues in live preview drawing path
