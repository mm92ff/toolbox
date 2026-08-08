from __future__ import annotations

from pathlib import Path

from app import constants
from app.state.folder_browse_appearance import (
    FolderBrowseAppearanceStore,
    normalize_folder_path,
)


def test_path_normalization_unifies_equivalent_paths(tmp_path: Path) -> None:
    nested = tmp_path / "folder"
    nested.mkdir()

    assert normalize_folder_path(nested) == normalize_folder_path(
        nested.parent / "." / nested.name
    )


def test_path_normalization_resolves_symlinks(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)

    assert normalize_folder_path(link) == normalize_folder_path(target)


def test_override_precedence_reset_and_global_fallback(tmp_path: Path) -> None:
    store = FolderBrowseAppearanceStore()

    assert store.effective_icon_size(tmp_path, 88) == 88
    assert store.set_icon_size(tmp_path, 116) is True
    assert store.effective_icon_size(tmp_path, 88) == 116
    assert store.reset_icon_size(tmp_path) is True
    assert store.effective_icon_size(tmp_path, 88) == 88


def test_sizes_are_clamped_and_boolean_values_are_rejected(tmp_path: Path) -> None:
    store = FolderBrowseAppearanceStore()

    assert store.set_icon_size(tmp_path, -100) is True
    assert store.get_override(tmp_path) == constants.MIN_ICON_SIZE
    assert store.set_icon_size(tmp_path, 1000) is True
    assert store.get_override(tmp_path) == constants.MAX_ICON_SIZE
    assert store.set_icon_size(tmp_path, True) is False
    assert store.get_override(tmp_path) == constants.MAX_ICON_SIZE


def test_identical_value_is_a_noop(tmp_path: Path) -> None:
    store = FolderBrowseAppearanceStore()
    store.set_icon_size(tmp_path, 96)
    revision = store.revision

    assert store.set_icon_size(tmp_path, 96) is False
    assert store.revision == revision


def test_snapshot_roundtrip_ignores_invalid_records(tmp_path: Path) -> None:
    valid_path = tmp_path / "valid"
    store = FolderBrowseAppearanceStore()

    changed = store.load_snapshot(
        {
            "icon_size_overrides": {
                str(valid_path): {"size": 104, "last_used_utc": "2026-08-08T10:00:00Z"},
                "": {"size": 80},
                str(tmp_path / "bad_bool"): {"size": False},
                str(tmp_path / "bad_text"): {"size": "large"},
            }
        }
    )

    assert changed is True
    assert store.get_override(valid_path) == 104
    assert len(store.build_snapshot()["icon_size_overrides"]) == 1


def test_compact_legacy_snapshot_shape_is_accepted(tmp_path: Path) -> None:
    store = FolderBrowseAppearanceStore()

    assert store.load_snapshot(
        {"icon_size_overrides": {str(tmp_path): 92}}
    ) is True
    assert store.get_override(tmp_path) == 92


def test_snapshot_is_defensive(tmp_path: Path) -> None:
    store = FolderBrowseAppearanceStore()
    store.set_icon_size(tmp_path, 100)
    snapshot = store.build_snapshot()
    overrides = snapshot["icon_size_overrides"]
    assert isinstance(overrides, dict)
    overrides.clear()

    assert store.get_override(tmp_path) == 100


def test_lru_limit_removes_oldest_record(tmp_path: Path) -> None:
    store = FolderBrowseAppearanceStore(max_entries=2)
    first = tmp_path / "first"
    second = tmp_path / "second"
    third = tmp_path / "third"
    store.load_snapshot(
        {
            "icon_size_overrides": {
                str(first): {"size": 80, "last_used_utc": "2026-01-01T00:00:00Z"},
                str(second): {"size": 88, "last_used_utc": "2026-02-01T00:00:00Z"},
            }
        }
    )

    store.set_icon_size(third, 96)

    assert store.get_override(first) is None
    assert store.get_override(second) == 88
    assert store.get_override(third) == 96
