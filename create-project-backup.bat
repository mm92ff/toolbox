@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%" || goto :project_root_error

set "PROJECT_NAME=toolbox"
set "SELF_TEST=0"
if /i "%~1"=="--self-test" set "SELF_TEST=1"

call :find_7zip
if errorlevel 1 goto :missing_7zip

for /f "usebackq delims=" %%I in (`powershell.exe -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'"`) do set "TIMESTAMP=%%I"
if not defined TIMESTAMP goto :timestamp_error

if "%SELF_TEST%"=="1" (
    set "ARCHIVE_NAME=%PROJECT_NAME%_backup_self-test.7z"
) else (
    set "ARCHIVE_NAME=%PROJECT_NAME%_backup_%TIMESTAMP%.7z"
)
set "ARCHIVE_PATH=%SCRIPT_DIR%%ARCHIVE_NAME%"

if exist "%ARCHIVE_PATH%" del /q "%ARCHIVE_PATH%" >nul 2>&1

if "%SELF_TEST%"=="1" goto :show_self_test_banner

echo.
echo Project backup
echo ==============
echo Project:   %PROJECT_NAME%
echo Output:    %ARCHIVE_PATH%
echo.
echo WARNING: This archive is not encrypted.
echo It contains the Git history, local source changes, tests, assets,
echo dependency files, and project helper scripts.
echo Generated files and the local Python environment are excluded.
echo Store the archive in a protected location.
echo.
goto :banner_complete

:show_self_test_banner
echo Running project backup self-test...

:banner_complete

"%SEVEN_ZIP%" a -t7z "%ARCHIVE_PATH%" "." ^
    -mx=7 -m0=lzma2 ^
    -xr!build -xr!dist -xr!dist-appimage -xr!Toolbox.AppDir -xr!thirdparty -xr!.bin ^
    -xr!__pycache__ -xr!.pytest_cache -xr!.mypy_cache -xr!.ruff_cache ^
    -xr!.tox -xr!.nox -xr!.hypothesis -xr!htmlcov ^
    -xr!.venv -xr!venv -xr!env -xr!*.egg-info ^
    -xr!*.pyc -xr!*.pyo -xr!.coverage -xr!coverage.xml ^
    -xr!*.log -xr!*.lnk -xr!*.exe -xr!*.AppImage -xr!*.AppImage.sha256 ^
    -xr!*.7z -xr!*.zip -xr!*.rar ^
    -xr!.DS_Store -xr!Thumbs.db
if errorlevel 1 goto :archive_failed

echo.
echo Verifying archive integrity...
"%SEVEN_ZIP%" t "%ARCHIVE_PATH%" -bsp0
if errorlevel 1 goto :verification_failed

if "%SELF_TEST%"=="1" goto :validate_self_test

for %%I in ("%ARCHIVE_PATH%") do set "ARCHIVE_SIZE=%%~zI"
echo.
echo Backup created and verified successfully.
echo File:  %ARCHIVE_PATH%
echo Bytes: %ARCHIVE_SIZE%
echo.
pause
exit /b 0

:validate_self_test
set "LIST_FILE=%TEMP%\%PROJECT_NAME%-backup-list-%RANDOM%%RANDOM%.txt"
"%SEVEN_ZIP%" l -slt "%ARCHIVE_PATH%" >"%LIST_FILE%"
if errorlevel 1 goto :self_test_failed

for %%R in (
    ".git\HEAD"
    "README.md"
    "LICENSE"
    "main.py"
    "pyproject.toml"
    "requirements.txt"
    "requirements-dev.txt"
    "toolbox_lightweight.spec"
    "toolbox_linux.spec"
    "start-toolbox.bat"
    "create-project-backup.bat"
    "Toolbox-Code-Backup.desktop"
    "scripts\create_code_backup.sh"
    "scripts\build-appimage.sh"
    "app\constants.py"
    "app\application_controller.py"
    "app\main_window.py"
    "app\services\folder_count.py"
    "app\assets\one.png"
    "app\features\settings\controller.py"
    "tests\test_runtime_config.py"
) do (
    findstr.exe /i /l /c:"Path = %%~R" "%LIST_FILE%" >nul
    if errorlevel 1 (
        set "MISSING_ENTRY=%%~R"
        goto :missing_required_entry
    )
)

powershell.exe -NoProfile -Command "$bad = Get-Content -LiteralPath $env:LIST_FILE | Where-Object { $_ -match '^Path = (?![A-Za-z]:[\\/])(?:(?:.*\\)?(?:build|dist|dist-appimage|Toolbox\.AppDir|thirdparty|\.bin|__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.tox|\.nox|\.hypothesis|htmlcov|\.venv|venv|env|[^\\]+\.egg-info)(?:\\|$)|.*(?:\.pyc|\.pyo|\.log|\.lnk|\.exe|\.AppImage|\.AppImage\.sha256|\.7z|\.zip|\.rar)$|(?:.*\\)?(?:\.coverage|coverage\.xml)$)' }; if ($bad) { $bad | Select-Object -First 20; exit 1 }"
if errorlevel 1 goto :found_excluded_entry

del /q "%LIST_FILE%" >nul 2>&1
del /q "%ARCHIVE_PATH%" >nul 2>&1
echo.
echo Self-test passed: integrity, required content, and exclusions are correct.
exit /b 0

:find_7zip
set "SEVEN_ZIP="
for %%E in (7z.exe 7zz.exe) do (
    if not defined SEVEN_ZIP for /f "delims=" %%P in ('where.exe %%E 2^>nul') do set "SEVEN_ZIP=%%P"
)
if defined SEVEN_ZIP exit /b 0
if exist "%ProgramFiles%\7-Zip\7z.exe" set "SEVEN_ZIP=%ProgramFiles%\7-Zip\7z.exe"
if defined SEVEN_ZIP exit /b 0
if exist "%ProgramFiles(x86)%\7-Zip\7z.exe" set "SEVEN_ZIP=%ProgramFiles(x86)%\7-Zip\7z.exe"
if defined SEVEN_ZIP exit /b 0
exit /b 1

:archive_failed
echo.
echo [ERROR] 7-Zip could not create the archive. Partial output is removed.
if exist "%ARCHIVE_PATH%" del /q "%ARCHIVE_PATH%" >nul 2>&1
goto :failed

:verification_failed
echo.
echo [ERROR] Archive verification failed. Unverified output is removed.
if exist "%ARCHIVE_PATH%" del /q "%ARCHIVE_PATH%" >nul 2>&1
goto :failed

:self_test_failed
echo.
echo [ERROR] Project backup self-test failed.
if defined LIST_FILE if exist "%LIST_FILE%" del /q "%LIST_FILE%" >nul 2>&1
if exist "%ARCHIVE_PATH%" del /q "%ARCHIVE_PATH%" >nul 2>&1
goto :failed

:missing_required_entry
echo [ERROR] Required project entry is missing from the backup: %MISSING_ENTRY%
goto :self_test_failed

:found_excluded_entry
echo [ERROR] An excluded generated entry is present in the backup.
goto :self_test_failed

:missing_7zip
echo [ERROR] 7-Zip was not found in PATH or a standard installation folder.
echo Install 7-Zip and run this script again.
goto :failed

:timestamp_error
echo [ERROR] Could not create a timestamp with PowerShell.
goto :failed

:project_root_error
echo [ERROR] Could not open the project root: %SCRIPT_DIR%
goto :failed

:failed
if "%SELF_TEST%"=="0" pause
exit /b 1
