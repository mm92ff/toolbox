[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $IsWindows) {
    throw "The Toolbox Windows release must be built on Windows."
}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DistRoot = Join-Path $ProjectRoot "dist-windows"
$PyInstallerDist = Join-Path $ProjectRoot "dist\windows"
$PyInstallerWork = Join-Path $ProjectRoot "build\windows"
$LicenseRoot = Join-Path $ProjectRoot "build\windows-release-licenses"

$Version = (& python -c "from app.constants import VERSION; print(VERSION)").Trim()
if ($LASTEXITCODE -ne 0 -or $Version -notmatch '^[A-Za-z0-9][A-Za-z0-9._+-]*$') {
    throw "Toolbox version could not be determined safely."
}

$ExpectedVersions = [ordered]@{
    "PySide6" = "6.11.1"
    "pyinstaller" = "6.21.0"
}
foreach ($Package in $ExpectedVersions.Keys) {
    $Actual = (& python -c "from importlib.metadata import version; print(version('$Package'))").Trim()
    if ($LASTEXITCODE -ne 0 -or $Actual -ne $ExpectedVersions[$Package]) {
        throw "Unexpected $Package version: expected $($ExpectedVersions[$Package]), got $Actual"
    }
}

foreach ($Path in @($DistRoot, $PyInstallerDist, $PyInstallerWork, $LicenseRoot)) {
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Path | Out-Null
}

$PythonLicense = (& python -c "import sys; from pathlib import Path; candidates=(Path(sys.base_prefix)/'LICENSE.txt', Path(sys.base_prefix)/'LICENSE'); print(next(str(p) for p in candidates if p.is_file()))").Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $PythonLicense -PathType Leaf)) {
    throw "Python license file was not found."
}
Copy-Item -LiteralPath $PythonLicense -Destination (Join-Path $LicenseRoot "PYTHON-LICENSE.txt")

$PyInstallerLicense = (& python -c "from importlib.metadata import distribution; d=distribution('pyinstaller'); p=next(p for p in d.files if str(p).replace('\\','/').endswith('licenses/COPYING.txt')); print(d.locate_file(p))").Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $PyInstallerLicense -PathType Leaf)) {
    throw "PyInstaller license file was not found."
}
Copy-Item -LiteralPath $PyInstallerLicense -Destination (Join-Path $LicenseRoot "PYINSTALLER-COPYING.txt")

$GnuLicenses = @(
    @{
        Name = "QT-LGPL-3.0.txt"
        Url = "https://www.gnu.org/licenses/lgpl-3.0.txt"
        Sha256 = "e3a994d82e644b03a792a930f574002658412f62407f5fee083f2555c5f23118"
    },
    @{
        Name = "QT-GPL-3.0.txt"
        Url = "https://www.gnu.org/licenses/gpl-3.0.txt"
        Sha256 = "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986"
    }
)
foreach ($License in $GnuLicenses) {
    $Target = Join-Path $LicenseRoot $License.Name
    & curl.exe `
        --fail `
        --location `
        --silent `
        --show-error `
        --retry 4 `
        --retry-all-errors `
        --connect-timeout 15 `
        --max-time 120 `
        --output $Target `
        $License.Url
    if ($LASTEXITCODE -ne 0) {
        throw "License download failed for $($License.Name) with exit code $LASTEXITCODE."
    }
    $ActualHash = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ActualHash -ne $License.Sha256) {
        throw "License checksum mismatch for $($License.Name): $ActualHash"
    }
}

$Commit = (& git -C $ProjectRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $Commit -notmatch '^[0-9a-f]{40}$') {
    throw "Git commit could not be determined."
}
$PythonVersion = (& python --version).Trim()
$PyInstallerVersion = (& python -m PyInstaller --version).Trim()
$PySideVersion = (& python -c "import PySide6; print(PySide6.__version__)").Trim()
@(
    "Toolbox version: $Version"
    "Git commit: $Commit"
    "Architecture: windows-x86_64"
    "$PythonVersion"
    "PyInstaller $PyInstallerVersion"
    "PySide6 $PySideVersion"
    "FFmpeg bundled: no"
) | Set-Content -LiteralPath (Join-Path $LicenseRoot "WINDOWS-BUILD-INFO.txt") -Encoding utf8

$env:TOOLBOX_WINDOWS_LICENSE_DIR = $LicenseRoot
& python -m PyInstaller `
    --clean `
    --noconfirm `
    --workpath $PyInstallerWork `
    --distpath $PyInstallerDist `
    (Join-Path $ProjectRoot "toolbox_lightweight.spec")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller Windows build failed."
}

$BuiltExe = Join-Path $PyInstallerDist "toolbox_lightweight.exe"
$ReleaseName = "Toolbox-$Version-windows-x86_64"
$ReleaseExe = Join-Path $DistRoot "$ReleaseName.exe"
if (-not (Test-Path -LiteralPath $BuiltExe -PathType Leaf)) {
    throw "Expected Windows executable was not produced: $BuiltExe"
}
Copy-Item -LiteralPath $BuiltExe -Destination $ReleaseExe

$SmokeRoot = Join-Path ([System.IO.Path]::GetTempPath()) "toolbox-$Commit-smoke"
if (Test-Path -LiteralPath $SmokeRoot) {
    Remove-Item -LiteralPath $SmokeRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $SmokeRoot | Out-Null
$SmokeReport = Join-Path $SmokeRoot "report.json"
$OriginalAppData = $env:APPDATA
$OriginalSmokeTest = $env:TOOLBOX_SMOKE_TEST
$OriginalSmokeReport = $env:TOOLBOX_SMOKE_REPORT
try {
    $env:APPDATA = Join-Path $SmokeRoot "appdata"
    $env:TOOLBOX_SMOKE_TEST = "1"
    $env:TOOLBOX_SMOKE_REPORT = $SmokeReport
    $Process = Start-Process -FilePath $ReleaseExe -ArgumentList "--smoke-test", "--windows-smoke-token" -Wait -PassThru
    if ($Process.ExitCode -ne 0) {
        throw "Windows executable smoke test exited with code $($Process.ExitCode)."
    }
} finally {
    $env:APPDATA = $OriginalAppData
    $env:TOOLBOX_SMOKE_TEST = $OriginalSmokeTest
    $env:TOOLBOX_SMOKE_REPORT = $OriginalSmokeReport
}
if (-not (Test-Path -LiteralPath $SmokeReport -PathType Leaf)) {
    throw "Windows executable did not create its smoke-test report."
}
$Smoke = Get-Content -LiteralPath $SmokeReport -Raw | ConvertFrom-Json
if (-not $Smoke.frozen -or $Smoke.qt_platform -ne "windows" -or $Smoke.application_name -ne "Toolbox") {
    throw "Windows executable smoke-test report contains unexpected runtime identity."
}
if ($Smoke.arguments -notcontains "--windows-smoke-token") {
    throw "Windows executable did not receive the forwarding token."
}

$BundleRoot = Join-Path $DistRoot $ReleaseName
New-Item -ItemType Directory -Path (Join-Path $BundleRoot "licenses") -Force | Out-Null
Copy-Item -LiteralPath $ReleaseExe -Destination $BundleRoot
foreach ($Document in @("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md")) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot $Document) -Destination $BundleRoot
}
Copy-Item -Path (Join-Path $LicenseRoot "*") -Destination (Join-Path $BundleRoot "licenses")

$ZipPath = Join-Path $DistRoot "$ReleaseName.zip"
Compress-Archive -Path $BundleRoot -DestinationPath $ZipPath -CompressionLevel Optimal
$ExeHash = (Get-FileHash -LiteralPath $ReleaseExe -Algorithm SHA256).Hash.ToLowerInvariant()
$ZipHash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
"$ExeHash  $([System.IO.Path]::GetFileName($ReleaseExe))" | Set-Content -LiteralPath "$ReleaseExe.sha256" -Encoding ascii
"$ZipHash  $([System.IO.Path]::GetFileName($ZipPath))" | Set-Content -LiteralPath "$ZipPath.sha256" -Encoding ascii

Write-Host "Windows EXE: $ReleaseExe"
Write-Host "Windows bundle: $ZipPath"
Write-Host "Commit: $Commit"
