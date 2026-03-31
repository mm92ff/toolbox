# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

### Added

- Keyboard undo/redo support (`Ctrl+Z` / `Ctrl+Y`)
- Context-menu action to add sections from empty canvas space
- Section color manager covering separators from all toolbox tabs
- Bulk and quick-apply controls for all separator line/title colors
- Separate separator spacing controls: `Gap Above` and `Gap Below`
- Help tab content expanded with current behavior and layout rules

### Changed

- Refactored settings code into focused modules (`state`, `apply`, `appearance`, `section_colors`, `io`, `profile`)
- Refactored canvas code into focused surface modules (`surface_state`, `surface_render`, `surface_geometry`, `surface_drag`, `surface_interaction`)
- Updated settings persistence to store asymmetric separator spacing while keeping legacy `section_gap` compatibility
- Updated separator layout engine to use asymmetric protected zones (above/below)
- Updated README documentation to reflect current features and behavior

### Fixed

- Multiple multi-select drag issues (horizontal drift, overlap/stacking, structural instability)
- Section drop hint behavior now works consistently in mixed multi-select scenarios
- Inconsistent post-drop spacing behavior near separators
- Broken-entry diagnostics flow hardened to avoid UI hangs by using non-blocking dialog handling
