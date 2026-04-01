# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

### Added

- `THIRD_PARTY_NOTICES.md` with FFmpeg/FFprobe licensing, provenance, and source-reference guidance for distributed binaries
- New FFmpeg section in Settings with detected source/status, resolved path display, manual path input, browse, and rescan controls
- Windows common-location FFmpeg discovery (Program Files, Chocolatey, Scoop, WinGet package folders)

### Changed

- README now includes a dedicated third-party licensing section pointing to FFmpeg compliance notes
- FFmpeg resolution order is now: environment override -> manual Settings path -> local/system install (PATH/common locations) -> bundled internal fallback

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
