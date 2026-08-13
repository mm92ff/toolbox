[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $IsWindows) {
    throw "The Windows release test selection must run on Windows."
}

# These modules validate Linux packaging, Linux desktop integration, POSIX file
# permissions/symlinks, or Linux-only command preparation. They remain mandatory
# in scripts/verify-linux-release.sh and are not meaningful on a Windows host.
$LinuxSpecificModules = @(
    "tests/test_appimage_packaging.py"
    "tests/test_code_backup.py"
    "tests/test_deb_packaging.py"
    "tests/test_desktop_entry_drop.py"
    "tests/test_desktop_entry_launch.py"
    "tests/test_development_desktop.py"
    "tests/test_ffmpeg_downloader.py"
    "tests/test_file_associations.py"
    "tests/test_folder_count_service.py"
    "tests/test_icon_resolution_security.py"
    "tests/test_linux_desktop_icons.py"
    "tests/test_linux_launch.py"
    "tests/test_responsive_layout.py"
    "tests/test_size_calculator.py"
    "tests/test_toolbox_diagnostics.py"
)

$PytestArguments = @("-m", "pytest", "-q", "tests")
foreach ($Module in $LinuxSpecificModules) {
    $PytestArguments += "--ignore=$Module"
}
& python @PytestArguments
if ($LASTEXITCODE -ne 0) {
    throw "Windows-compatible pytest selection failed with exit code $LASTEXITCODE."
}

& python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    throw "Ruff failed with exit code $LASTEXITCODE."
}
