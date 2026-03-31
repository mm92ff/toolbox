import unittest

from app import constants
from app.features.settings.profile import MainWindowSettingsProfileMixin


class SettingsProfileValidationTests(unittest.TestCase):
    def test_parse_imported_tabs_requires_list(self) -> None:
        with self.assertRaises(ValueError):
            MainWindowSettingsProfileMixin._parse_imported_tabs({"tabs": []})

    def test_parse_imported_tabs_requires_object_items(self) -> None:
        with self.assertRaises(ValueError):
            MainWindowSettingsProfileMixin._parse_imported_tabs(["bad-item"])

    def test_parse_imported_tabs_reports_malformed_tab(self) -> None:
        raw_tabs = [
            {
                "title": "Work",
                "entries": [
                    {
                        "title": "Broken",
                        "kind": "unknown",
                        "path": r"C:\Tools\broken.exe",
                    }
                ],
            }
        ]

        with self.assertRaises(ValueError):
            MainWindowSettingsProfileMixin._parse_imported_tabs(raw_tabs)

    def test_parse_imported_tabs_empty_list_uses_default_primary_tab(self) -> None:
        parsed = MainWindowSettingsProfileMixin._parse_imported_tabs([])

        self.assertEqual(1, len(parsed))
        self.assertTrue(parsed[0].is_primary)
        self.assertEqual(constants.DEFAULT_TOOLBOX_TAB_TITLE, parsed[0].title)

    def test_normalize_primary_tab_keeps_single_primary(self) -> None:
        parsed = MainWindowSettingsProfileMixin._parse_imported_tabs(
            [
                {"title": "A", "is_primary": True, "entries": []},
                {"title": "B", "is_primary": True, "entries": []},
            ]
        )

        MainWindowSettingsProfileMixin._normalize_primary_tab(parsed)

        self.assertTrue(parsed[0].is_primary)
        self.assertFalse(parsed[1].is_primary)

    def test_validate_profile_schema_version_rejects_non_integer(self) -> None:
        with self.assertRaises(ValueError):
            MainWindowSettingsProfileMixin._validate_profile_schema_version(
                {"schema_version": "1"}
            )

    def test_validate_profile_schema_version_rejects_newer_schema(self) -> None:
        with self.assertRaises(ValueError):
            MainWindowSettingsProfileMixin._validate_profile_schema_version({"schema_version": 2})

    def test_validate_toolbox_state_version_rejects_non_integer(self) -> None:
        with self.assertRaises(ValueError):
            MainWindowSettingsProfileMixin._validate_toolbox_state_version({"version": "3"})

    def test_validate_toolbox_state_version_rejects_newer_version(self) -> None:
        with self.assertRaises(ValueError):
            MainWindowSettingsProfileMixin._validate_toolbox_state_version({"version": 4})


if __name__ == "__main__":
    unittest.main()
