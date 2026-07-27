from __future__ import annotations

from pathlib import Path

import pytest

from app.services.desktop_entries import (
    MAX_DESKTOP_ENTRY_BYTES,
    DesktopEntryError,
    DesktopLaunchInput,
    DesktopLaunchItem,
    clear_desktop_entry_cache,
    desktop_entry_accepts_drop,
    desktop_entry_file_field_code,
    expand_desktop_exec,
    expand_desktop_exec_many,
    read_desktop_entry,
)


def _write_desktop(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def _application(
    tmp_path: Path,
    exec_line: str,
    *,
    extra: str = "",
    name: str = "Example",
) -> Path:
    return _write_desktop(
        tmp_path / "Example.desktop",
        (
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={name}\n"
            f"Exec={exec_line}\n"
            f"{extra}"
        ),
    )


def test_reads_application_metadata_and_localized_name(tmp_path: Path) -> None:
    path = _write_desktop(
        tmp_path / "Localized.desktop",
        (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Default\n"
            "Name[de]=Deutsch\n"
            "Name[de_CH]=Schweiz\n"
            "Exec=/usr/bin/true\n"
            "Icon=preferences-system\n"
            "TryExec=true\n"
            "Path=/tmp\n"
            "Terminal=false\n"
            "DBusActivatable=false\n"
            "MimeType=text/plain;inode/directory;\n"
            "NoDisplay=true\n"
        ),
    )

    metadata = read_desktop_entry(path, locale_name="de_CH.UTF-8")

    assert metadata.name == "Schweiz"
    assert metadata.icon == "preferences-system"
    assert metadata.try_exec == "true"
    assert metadata.working_directory == "/tmp"
    assert metadata.mime_types == ("text/plain", "inode/directory")
    assert metadata.no_display is True
    assert metadata.terminal is False


def test_name_falls_back_from_language_to_default(tmp_path: Path) -> None:
    path = _write_desktop(
        tmp_path / "Localized.desktop",
        (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Default\n"
            "Name[de]=Deutsch\n"
            "Exec=/usr/bin/true\n"
        ),
    )

    assert read_desktop_entry(path, locale_name="de_AT").name == "Deutsch"
    assert read_desktop_entry(path, locale_name="fr_FR").name == "Default"


def test_utf8_bom_and_escaped_string_values_are_supported(tmp_path: Path) -> None:
    path = tmp_path / "BOM.desktop"
    path.write_bytes(
        (
            "\ufeff[Desktop Entry]\n"
            "Type=Application\n"
            "Name=One\\sTwo\n"
            "Exec=/usr/bin/true\n"
        ).encode("utf-8")
    )

    assert read_desktop_entry(path).name == "One Two"


def test_oversized_desktop_entry_is_rejected_before_reading(tmp_path: Path) -> None:
    path = tmp_path / "Oversized.desktop"
    path.write_bytes(b"x" * (MAX_DESKTOP_ENTRY_BYTES + 1))

    with pytest.raises(DesktopEntryError, match="exceeds"):
        read_desktop_entry(path)


def test_invalid_utf8_is_reported_as_desktop_entry_error(tmp_path: Path) -> None:
    path = tmp_path / "Invalid.desktop"
    path.write_bytes(
        b"[Desktop Entry]\nType=Application\nName=\xff\nExec=/usr/bin/true\n"
    )

    with pytest.raises(DesktopEntryError, match="not valid UTF-8"):
        read_desktop_entry(path)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("Type=Application\nName=Bad\nExec=/usr/bin/true\n", "outside a group"),
        ("[Desktop Entry]\nName=Bad\nExec=/usr/bin/true\n", "missing Type"),
        ("[Desktop Entry]\nType=Application\nName=Bad\n", "missing Exec"),
        ("[Desktop Entry]\nType=Unknown\nName=Bad\nExec=/usr/bin/true\n", "unsupported Type"),
        (
            "[Desktop Entry]\nType=Application\nName=Bad\nExec=/usr/bin/true\nTerminal=maybe\n",
            "must be true or false",
        ),
    ],
)
def test_invalid_desktop_entries_are_rejected(
    tmp_path: Path,
    body: str,
    message: str,
) -> None:
    path = _write_desktop(tmp_path / "Bad.desktop", body)

    with pytest.raises(DesktopEntryError, match=message):
        read_desktop_entry(path)


def test_link_entry_requires_and_exposes_url(tmp_path: Path) -> None:
    path = _write_desktop(
        tmp_path / "Link.desktop",
        (
            "[Desktop Entry]\n"
            "Type=Link\n"
            "Name=Example Site\n"
            "URL=https://example.com/\n"
            "Icon=web-browser\n"
        ),
    )

    metadata = read_desktop_entry(path)

    assert metadata.is_link
    assert metadata.url == "https://example.com/"


def test_problematic_python_percent_k_wrapper_is_expanded(tmp_path: Path) -> None:
    path = _application(
        tmp_path,
        (
            "/usr/bin/python3 -c "
            "\"import os,sys; "
            "os.execl('/bin/bash','bash',"
            "os.path.join(os.path.dirname(sys.argv[1]),"
            "'scripts','example.sh'))\" %k"
        ),
    )

    command = expand_desktop_exec(read_desktop_entry(path))

    assert command[:2] == ("/usr/bin/python3", "-c")
    assert "sys.argv[1]" in command[2]
    assert command[3] == str(path.resolve())


def test_percent_f_expands_multiple_local_paths(tmp_path: Path) -> None:
    desktop = _application(tmp_path, "/usr/bin/printf %F")
    first = tmp_path / "one file.txt"
    second = tmp_path / "zwei.txt"
    launch_input = DesktopLaunchInput.from_local_paths((first, second))

    metadata = read_desktop_entry(desktop)
    command = expand_desktop_exec(metadata, launch_input)

    assert desktop_entry_accepts_drop(metadata)
    assert desktop_entry_file_field_code(metadata) == "F"
    assert command == ("/usr/bin/printf", str(first), str(second))


def test_percent_u_preserves_order_and_urls(tmp_path: Path) -> None:
    desktop = _application(tmp_path, "/usr/bin/printf %U")
    launch_input = DesktopLaunchInput(
        (
            DesktopLaunchItem(
                url=(tmp_path / "local.txt").resolve().as_uri(),
                local_path=str(tmp_path / "local.txt"),
            ),
            DesktopLaunchItem(url="https://example.com/a%20b"),
        )
    )

    command = expand_desktop_exec(read_desktop_entry(desktop), launch_input)

    assert command == (
        "/usr/bin/printf",
        (tmp_path / "local.txt").resolve().as_uri(),
        "https://example.com/a%20b",
    )


def test_percent_f_rejects_remote_urls(tmp_path: Path) -> None:
    desktop = _application(tmp_path, "/usr/bin/printf %F")
    launch_input = DesktopLaunchInput((DesktopLaunchItem(url="https://example.com"),))

    with pytest.raises(DesktopEntryError, match="local files only"):
        expand_desktop_exec(read_desktop_entry(desktop), launch_input)


def test_declared_mime_type_rejects_incompatible_local_file(
    tmp_path: Path,
) -> None:
    desktop = _application(
        tmp_path,
        "/usr/bin/printf %F",
        extra="MimeType=application/x-mswinurl;\n",
    )
    launch_input = DesktopLaunchInput(
        (
            DesktopLaunchItem.from_local_path(
                tmp_path / "plain.txt",
                mime_type="text/plain",
            ),
        )
    )

    with pytest.raises(DesktopEntryError, match="not declared"):
        expand_desktop_exec(read_desktop_entry(desktop), launch_input)


def test_octet_stream_mime_declaration_accepts_regular_local_files(
    tmp_path: Path,
) -> None:
    desktop = _application(
        tmp_path,
        "/usr/bin/printf %U",
        extra="MimeType=inode/directory;application/octet-stream;\n",
    )
    local = tmp_path / "picture.png"
    launch_input = DesktopLaunchInput(
        (
            DesktopLaunchItem.from_local_path(
                local,
                mime_type="image/png",
            ),
        )
    )

    assert expand_desktop_exec(read_desktop_entry(desktop), launch_input)[-1] == (
        local.resolve().as_uri()
    )


def test_lowercase_file_code_builds_one_command_per_item(tmp_path: Path) -> None:
    desktop = _application(tmp_path, "/usr/bin/printf %f")
    launch_input = DesktopLaunchInput.from_local_paths(
        (tmp_path / "first", tmp_path / "second")
    )

    commands = expand_desktop_exec_many(read_desktop_entry(desktop), launch_input)

    assert commands == (
        ("/usr/bin/printf", str(tmp_path / "first")),
        ("/usr/bin/printf", str(tmp_path / "second")),
    )


def test_file_code_is_removed_for_a_normal_click(tmp_path: Path) -> None:
    desktop = _application(tmp_path, "/usr/bin/printf %F")

    assert expand_desktop_exec(read_desktop_entry(desktop)) == ("/usr/bin/printf",)


def test_drop_on_entry_without_file_code_is_rejected(tmp_path: Path) -> None:
    desktop = _application(tmp_path, "/usr/bin/true")

    with pytest.raises(DesktopEntryError, match="does not accept"):
        expand_desktop_exec(
            read_desktop_entry(desktop),
            DesktopLaunchInput.from_local_paths((tmp_path / "input",)),
        )


def test_icon_name_and_localized_name_field_codes(tmp_path: Path) -> None:
    desktop = _application(
        tmp_path,
        "/usr/bin/printf %i %c",
        extra="Icon=web-browser\n",
        name="Two Words",
    )

    assert expand_desktop_exec(read_desktop_entry(desktop)) == (
        "/usr/bin/printf",
        "--icon",
        "web-browser",
        "Two Words",
    )


def test_icon_field_code_without_declared_icon_adds_no_arguments(
    tmp_path: Path,
) -> None:
    desktop = _application(tmp_path, "/usr/bin/printf %i")

    assert expand_desktop_exec(read_desktop_entry(desktop)) == (
        "/usr/bin/printf",
    )


def test_literal_percent_and_deprecated_codes(tmp_path: Path) -> None:
    desktop = _application(
        tmp_path,
        "/usr/bin/printf 100%% %d %D %n %N %v %m",
    )

    assert expand_desktop_exec(read_desktop_entry(desktop)) == (
        "/usr/bin/printf",
        "100%",
    )


@pytest.mark.parametrize(
    ("exec_line", "message"),
    [
        ("/usr/bin/true %x", "unknown field code"),
        ("/usr/bin/true %F %U", "more than one"),
        ("/usr/bin/true prefix%F", "standalone"),
        ('/usr/bin/true "%k"', "must not be quoted"),
        ("/usr/bin/true 'unsafe'", "must be quoted"),
        ("/usr/bin/true \"unterminated", "unterminated quote"),
    ],
)
def test_invalid_exec_syntax_is_rejected(
    tmp_path: Path,
    exec_line: str,
    message: str,
) -> None:
    desktop = _application(tmp_path, exec_line)

    with pytest.raises(DesktopEntryError, match=message):
        expand_desktop_exec(read_desktop_entry(desktop))


def test_cache_is_invalidated_when_file_changes(tmp_path: Path) -> None:
    clear_desktop_entry_cache()
    path = _application(tmp_path, "/usr/bin/true", name="Before")
    first = read_desktop_entry(path)
    path.write_text(
        (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=After Value\n"
            "Exec=/usr/bin/true\n"
        ),
        encoding="utf-8",
    )

    second = read_desktop_entry(path)

    assert first.name == "Before"
    assert second.name == "After Value"
