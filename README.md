# Toolbox

Desktop toolbox launcher built with Python and PySide6.

## Screenshots

![Toolbox screenshot 1](screenshots/one.png)
![Toolbox screenshot 2](screenshots/two.png)

## Highlights

- Multiple toolbox tabs with reorder/visibility management
- Drag-and-drop app entries and section separators
- Multi-select movement with structure-preserving behavior
- Grid snapping with optional auto-compaction
- Separator protection and snapping with conflict hints
- Per-section and global separator/title color management (all tabs)
- Configurable separator spacing with separate `Gap Above` and `Gap Below`
- Tool launch options (args, working dir, wait mode, admin)
- Broken-entry diagnostics and optional cleanup
- JSON import/export for toolbox state and UI settings
- Keyboard undo/redo (`Ctrl+Z`, `Ctrl+Y`)

## Requirements

- Python 3.13
- PySide6
- pytest (for running tests)

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -U pip
pip install pyside6 pytest
```

## Run

```powershell
python main.py
```

## Test

```powershell
$env:PYTHONPATH='.'
pytest -q
```

## Usage Notes

- Most layout/style changes in `Settings` apply after `Save Apply`.
- Tile positions snap to the active grid, so visible spacing changes in row-sized steps.
- `Check Broken Entries` runs in the background and shows results when scanning is done.

## Project Layout

- `main.py`: app entry point
- `app/`: application modules (UI, features, services, domain)
- `tests/`: unit tests

## License

MIT License. See [LICENSE](LICENSE).
