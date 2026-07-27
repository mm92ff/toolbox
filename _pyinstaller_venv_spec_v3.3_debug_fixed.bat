@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==========================================
REM PyInstaller Helfer v3.3-debug-fixed
REM - mehr Debug-Ausgaben
REM - schreibt eine Debug-Logdatei ins Projekt
REM - CMD-Fenster bleibt bei Fehlern offen
REM - reparierte Errorlevel-Weitergabe
REM - robuste Aufloesung der Build-Ausgabe
REM ==========================================

set "SCRIPT_VERSION=3.3-debug-fixed"
set "PY_FILE="
set "PROJECT_DIR="
set "PY_BASENAME="
set "SPEC_FILE="
set "RUNNER_KIND="
set "RUNNER_PATH="
set "APP_NAME="
set "FINAL_ARTIFACT="
set "COPIED_ARTIFACT="
set "DIST_DIR="
set "BUILD_DIR="
set "TEMP_VENV_CREATED=0"
set "TEMP_VENV_PATH="
set "BOOTSTRAP_PY="
set "DEP_INSTALL_SOURCE="
set "DEP_INSTALL_METHOD="
set "DEBUG_LOG="
set "LAST_STEP=Start"
set "LAST_COMMAND="
set "LAST_ERRORLEVEL="
set "FAIL_REASON="
set "PAUSE_ON_ERROR=1"

set "LAST_STEP=Python-Datei bestimmen"
if not "%~1"=="" (
    if /I "%~x1"==".py" set "PY_FILE=%~f1"
)

if not defined PY_FILE set "PY_FILE=%~dp0main.py"

if not exist "%PY_FILE%" (
    set "FAIL_REASON=Python-Datei nicht gefunden"
    echo [FEHLER] Python-Datei nicht gefunden: "%PY_FILE%"
    echo Ziehe eine .py Datei auf diese .bat oder lege eine main.py daneben.
    goto :fail
)

for %%I in ("%PY_FILE%") do (
    set "PROJECT_DIR=%%~dpI"
    set "PY_BASENAME=%%~nI"
)
set "DIST_DIR=%PROJECT_DIR%dist"
set "BUILD_DIR=%PROJECT_DIR%build"
set "TEMP_VENV_PATH=%PROJECT_DIR%.venv"
set "DEBUG_LOG=%PROJECT_DIR%pyinstaller_debug.log"

> "%DEBUG_LOG%" echo [START] %date% %time% - PyInstaller Helfer v%SCRIPT_VERSION%
>> "%DEBUG_LOG%" echo [DEBUG] Batch-Datei: %~f0
>> "%DEBUG_LOG%" echo [DEBUG] Argument 1: %~1
>> "%DEBUG_LOG%" echo [DEBUG] PY_FILE: %PY_FILE%
>> "%DEBUG_LOG%" echo [DEBUG] PROJECT_DIR: %PROJECT_DIR%
>> "%DEBUG_LOG%" echo [DEBUG] DIST_DIR: %DIST_DIR%
>> "%DEBUG_LOG%" echo [DEBUG] BUILD_DIR: %BUILD_DIR%
>> "%DEBUG_LOG%" echo [DEBUG] TEMP_VENV_PATH: %TEMP_VENV_PATH%

pushd "%PROJECT_DIR%" >nul 2>nul || (
    set "FAIL_REASON=Konnte nicht in das Projektverzeichnis wechseln"
    echo [FEHLER] Konnte nicht in das Projektverzeichnis wechseln:
    echo          "%PROJECT_DIR%"
    >> "%DEBUG_LOG%" echo [FEHLER] pushd fehlgeschlagen: %PROJECT_DIR%
    goto :fail
)

>> "%DEBUG_LOG%" echo [DEBUG] Aktuelles Verzeichnis nach pushd: %CD%

echo [INFO] PyInstaller Helfer v%SCRIPT_VERSION%
echo [INFO] Verwende Python-Datei:
echo        "%PY_FILE%"
echo [INFO] Projektverzeichnis:
echo        "%PROJECT_DIR%"
echo [INFO] Debug-Log:
echo        "%DEBUG_LOG%"
echo.
echo [DEBUG] Projektinhalt (Kurzuebersicht):
if exist "%PROJECT_DIR%main.py" echo   - main.py gefunden
if exist "%PROJECT_DIR%app\main.py" echo   - app\main.py gefunden
if exist "%PROJECT_DIR%pyproject.toml" echo   - pyproject.toml gefunden
if exist "%PROJECT_DIR%requirements.txt" echo   - requirements.txt gefunden
for %%F in ("%PROJECT_DIR%*.spec") do if exist "%%~fF" echo   - spec: %%~nxF
echo.

set "LAST_STEP=Spec-Erkennung"
call :detect_and_select_spec
if errorlevel 1 goto :fail

echo.
set "LAST_STEP=Python-Umgebung waehlen"
call :select_python_runner
if errorlevel 1 goto :fail

echo.
set "LAST_STEP=Sauberer Build vorbereiten"
call :prepare_clean_build
if errorlevel 1 goto :fail

echo.
set "LAST_STEP=PyInstaller Build"
if defined SPEC_FILE (
    echo [INFO] Build mit vorhandener Spec-Datei.
    echo        "%SPEC_FILE%"
    >> "%DEBUG_LOG%" echo [INFO] Spec-Build: %SPEC_FILE%
    call :invoke_pyinstaller "%SPEC_FILE%"
) else (
    set "APP_NAME=%PY_BASENAME%"
    echo [INFO] Keine .spec-Datei gefunden. Es wird direkt aus der .py gebaut.
    echo [INFO] App-Name fuer Direkt-Build: "%APP_NAME%"
    >> "%DEBUG_LOG%" echo [INFO] Direkt-Build fuer: %PY_FILE%
    call :invoke_pyinstaller --onefile --windowed --name "%APP_NAME%" "%PY_FILE%"
)

if errorlevel 1 (
    set "LAST_ERRORLEVEL=!errorlevel!"
    set "FAIL_REASON=PyInstaller Build fehlgeschlagen"
    echo.
    echo [FEHLER] PyInstaller Build fehlgeschlagen.
    goto :fail
)

echo.
set "LAST_STEP=Build-Ausgabe aufloesen"
call :resolve_output
if errorlevel 1 goto :fail

echo.
set "LAST_STEP=Artefakt kopieren"
call :copy_final_artifact_to_project
if errorlevel 1 goto :fail

echo.
set "LAST_STEP=Build-Ordner aufraeumen"
call :cleanup_output_dirs
if errorlevel 1 goto :fail

echo.
set "LAST_STEP=Temporaere Venv aufraeumen"
call :cleanup_temp_venv
if errorlevel 1 goto :fail

echo.
echo [OK] Build abgeschlossen.
if defined COPIED_ARTIFACT (
    echo [INFO] EXE ins Projektverzeichnis kopiert:
    echo        "%COPIED_ARTIFACT%"
) else if defined FINAL_ARTIFACT (
    echo [INFO] Gefundenes Artefakt:
    echo        "%FINAL_ARTIFACT%"
) else (
    echo [INFO] Kein einzelnes EXE-Artefakt automatisch ermittelt.
)
>> "%DEBUG_LOG%" echo [OK] Build abgeschlossen.

goto :done

:detect_and_select_spec
set "SPEC_COUNT=0"
for %%F in ("%PROJECT_DIR%*.spec") do (
    if exist "%%~fF" (
        set /a SPEC_COUNT+=1
        set "SPEC_!SPEC_COUNT!=%%~fF"
    )
)
>> "%DEBUG_LOG%" echo [DEBUG] Gefundene Spec-Anzahl: !SPEC_COUNT!

if !SPEC_COUNT! EQU 0 (
    echo [INFO] Keine .spec-Datei im Projektverzeichnis gefunden.
    set "SPEC_FILE="
    exit /b 0
)

if !SPEC_COUNT! EQU 1 (
    set "SPEC_FILE=!SPEC_1!"
    echo [INFO] Eine .spec-Datei gefunden:
    echo        "!SPEC_1!"
    >> "%DEBUG_LOG%" echo [INFO] Eine Spec gefunden: !SPEC_1!
    exit /b 0
)

echo [INFO] Mehrere .spec-Dateien gefunden:
for /L %%N in (1,1,!SPEC_COUNT!) do (
    for %%F in ("!SPEC_%%N!") do echo   [%%N] %%~nxF
)

:spec_prompt
set "SPEC_CHOICE="
set /p "SPEC_CHOICE=Welche .spec soll verwendet werden? [1-!SPEC_COUNT!]: "
if not defined SPEC_CHOICE set "SPEC_CHOICE=1"
set "SPEC_FILE="
for /L %%N in (1,1,!SPEC_COUNT!) do (
    if "!SPEC_CHOICE!"=="%%N" set "SPEC_FILE=!SPEC_%%N!"
)
if not defined SPEC_FILE (
    echo [FEHLER] Ungueltige Auswahl.
    >> "%DEBUG_LOG%" echo [FEHLER] Ungueltige Spec-Auswahl: !SPEC_CHOICE!
    goto :spec_prompt
)

echo [INFO] Ausgewaehlte .spec-Datei:
for %%F in ("%SPEC_FILE%") do echo        "%%~fF"
>> "%DEBUG_LOG%" echo [INFO] Ausgewaehlte Spec: %SPEC_FILE%
exit /b 0

:select_python_runner
set "VENV_COUNT=0"

call :try_add_venv ".venv"
call :try_add_venv "venv"
call :try_add_venv "env"
call :try_add_venv ".env"

for /D %%D in (*) do (
    if exist "%%~fD\Scripts\python.exe" (
        call :add_venv_if_new "%%~nxD" "%%~fD\Scripts\python.exe"
    )
)
>> "%DEBUG_LOG%" echo [DEBUG] Gefundene lokale Python-Umgebungen: !VENV_COUNT!

echo [INFO] Python-Umgebung waehlen:
echo   [0] System / PATH
if !VENV_COUNT! GTR 0 (
    for /L %%N in (1,1,!VENV_COUNT!) do (
        echo   [%%N] !VENV_NAME_%%N!  ^(!VENV_PATH_%%N!^)
    )
) else (
    echo   [INFO] Keine lokale virtuelle Umgebung gefunden.
    echo          Erwartet wird z. B. ".venv\Scripts\python.exe"
)
echo   [T] Temporaere .venv erstellen, Build ausfuehren, .venv danach loeschen
echo   [C] Benutzerdefiniertes python.exe

:env_prompt
set "ENV_CHOICE="
set /p "ENV_CHOICE=Auswahl [0]: "
if not defined ENV_CHOICE set "ENV_CHOICE=0"

if /I "%ENV_CHOICE%"=="T" goto :temp_venv_runner
if /I "%ENV_CHOICE%"=="C" goto :custom_python
if "%ENV_CHOICE%"=="0" goto :system_runner

set "RUNNER_PATH="
for /L %%N in (1,1,!VENV_COUNT!) do (
    if "%ENV_CHOICE%"=="%%N" set "RUNNER_PATH=!VENV_PATH_%%N!"
)
if defined RUNNER_PATH (
    set "RUNNER_KIND=python"
    echo [INFO] Verwende venv / lokales python.exe:
    echo        "%RUNNER_PATH%"
    >> "%DEBUG_LOG%" echo [INFO] Runner: python via %RUNNER_PATH%
    exit /b 0
)

echo [FEHLER] Ungueltige Auswahl.
>> "%DEBUG_LOG%" echo [FEHLER] Ungueltige Umgebungs-Auswahl: %ENV_CHOICE%
goto :env_prompt

:temp_venv_runner
if exist "%TEMP_VENV_PATH%\Scripts\python.exe" (
    echo [FEHLER] Eine .venv existiert bereits:
    echo          "%TEMP_VENV_PATH%"
    echo          Bitte waehle die vorhandene venv aus der Liste oder loesche sie manuell.
    >> "%DEBUG_LOG%" echo [FEHLER] Temp-Venv existiert bereits: %TEMP_VENV_PATH%
    goto :env_prompt
)
call :create_temp_venv
exit /b !errorlevel!

:try_add_venv
if not "%~1"=="" (
    if exist "%PROJECT_DIR%%~1\Scripts\python.exe" (
        call :add_venv_if_new "%~1" "%PROJECT_DIR%%~1\Scripts\python.exe"
    )
)
exit /b 0

:add_venv_if_new
set "_ADD_NAME=%~1"
set "_ADD_PATH=%~2"
if not defined _ADD_PATH exit /b 0
if not exist "%_ADD_PATH%" exit /b 0
for /L %%N in (1,1,!VENV_COUNT!) do (
    if /I "!VENV_PATH_%%N!"=="!_ADD_PATH!" exit /b 0
)
set /a VENV_COUNT+=1
set "VENV_NAME_!VENV_COUNT!=!_ADD_NAME!"
set "VENV_PATH_!VENV_COUNT!=!_ADD_PATH!"
exit /b 0

:custom_python
set "CUSTOM_PY="
set /p "CUSTOM_PY=Pfad zu python.exe: "
if not defined CUSTOM_PY (
    echo [FEHLER] Kein Pfad eingegeben.
    >> "%DEBUG_LOG%" echo [FEHLER] Kein custom python.exe Pfad eingegeben.
    goto :env_prompt
)
if not exist "%CUSTOM_PY%" (
    echo [FEHLER] Datei nicht gefunden:
    echo          "%CUSTOM_PY%"
    >> "%DEBUG_LOG%" echo [FEHLER] Custom python.exe nicht gefunden: %CUSTOM_PY%
    goto :env_prompt
)
set "RUNNER_KIND=python"
set "RUNNER_PATH=%CUSTOM_PY%"
echo [INFO] Verwende benutzerdefiniertes python.exe:
echo        "%RUNNER_PATH%"
>> "%DEBUG_LOG%" echo [INFO] Runner: python via %RUNNER_PATH%
exit /b 0

:system_runner
where pyinstaller >nul 2>nul
if not errorlevel 1 (
    set "RUNNER_KIND=pyinstaller"
    set "RUNNER_PATH=pyinstaller"
    echo [INFO] Verwende PyInstaller direkt aus dem PATH.
    >> "%DEBUG_LOG%" echo [INFO] Runner: pyinstaller aus PATH
    exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
    set "RUNNER_KIND=py"
    set "RUNNER_PATH=py"
    echo [INFO] Verwende Python Launcher: py -m PyInstaller
    >> "%DEBUG_LOG%" echo [INFO] Runner: py -m PyInstaller
    exit /b 0
)

where python >nul 2>nul
if not errorlevel 1 (
    set "RUNNER_KIND=python"
    set "RUNNER_PATH=python"
    echo [INFO] Verwende System-Python: python -m PyInstaller
    >> "%DEBUG_LOG%" echo [INFO] Runner: python -m PyInstaller
    exit /b 0
)

echo [FEHLER] Weder pyinstaller noch py noch python wurden im PATH gefunden.
>> "%DEBUG_LOG%" echo [FEHLER] Kein pyinstaller/py/python im PATH gefunden.
exit /b 1

:create_temp_venv
set "BOOTSTRAP_PY="
where py >nul 2>nul
if not errorlevel 1 set "BOOTSTRAP_PY=py"
if not defined BOOTSTRAP_PY (
    where python >nul 2>nul
    if not errorlevel 1 set "BOOTSTRAP_PY=python"
)

if not defined BOOTSTRAP_PY (
    echo [FEHLER] Zum Erstellen einer .venv wird py oder python im PATH benoetigt.
    >> "%DEBUG_LOG%" echo [FEHLER] Kein Bootstrap-Python fuer .venv gefunden.
    exit /b 1
)

echo [INFO] Erstelle temporaere .venv:
echo        "%TEMP_VENV_PATH%"
>> "%DEBUG_LOG%" echo [INFO] Erstelle temporaere .venv: %TEMP_VENV_PATH%
"%BOOTSTRAP_PY%" -m venv "%TEMP_VENV_PATH%"
if errorlevel 1 (
    echo [FEHLER] Erstellen der .venv fehlgeschlagen.
    >> "%DEBUG_LOG%" echo [FEHLER] Erstellen der .venv fehlgeschlagen.
    exit /b 1
)

if not exist "%TEMP_VENV_PATH%\Scripts\python.exe" (
    echo [FEHLER] .venv wurde erstellt, aber python.exe fehlt:
    echo          "%TEMP_VENV_PATH%\Scripts\python.exe"
    >> "%DEBUG_LOG%" echo [FEHLER] python.exe in .venv fehlt.
    exit /b 1
)

set "TEMP_VENV_CREATED=1"
set "RUNNER_KIND=python"
set "RUNNER_PATH=%TEMP_VENV_PATH%\Scripts\python.exe"

echo [INFO] Aktualisiere pip in der temporaeren .venv...
>> "%DEBUG_LOG%" echo [INFO] pip-Upgrade in temporaerer .venv.
"%RUNNER_PATH%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [FEHLER] pip-Upgrade in der temporaeren .venv fehlgeschlagen.
    >> "%DEBUG_LOG%" echo [FEHLER] pip-Upgrade fehlgeschlagen.
    exit /b 1
)

echo [INFO] Installiere PyInstaller in der temporaeren .venv...
>> "%DEBUG_LOG%" echo [INFO] Installiere PyInstaller in temporaerer .venv.
"%RUNNER_PATH%" -m pip install pyinstaller
if errorlevel 1 (
    echo [FEHLER] Installation von PyInstaller in der temporaeren .venv fehlgeschlagen.
    >> "%DEBUG_LOG%" echo [FEHLER] PyInstaller-Installation fehlgeschlagen.
    exit /b 1
)

call :install_project_dependencies
if errorlevel 1 exit /b 1

echo [INFO] Verwende temporaere .venv fuer den Build:
echo        "%RUNNER_PATH%"
>> "%DEBUG_LOG%" echo [INFO] Runner: temporaere venv via %RUNNER_PATH%
exit /b 0

:install_project_dependencies
set "DEP_INSTALL_SOURCE="
set "DEP_INSTALL_METHOD="

if exist "%PROJECT_DIR%requirements.txt" (
    set "DEP_INSTALL_SOURCE=%PROJECT_DIR%requirements.txt"
    set "DEP_INSTALL_METHOD=pip install -r requirements.txt"
    echo [INFO] Abhaengigkeitsquelle erkannt: requirements.txt
    echo        "%DEP_INSTALL_SOURCE%"
    if exist "%PROJECT_DIR%pyproject.toml" (
        echo [INFO] Hinweis: pyproject.toml ist ebenfalls vorhanden, requirements.txt hat Vorrang.
        echo        "%PROJECT_DIR%pyproject.toml"
    )
    echo [INFO] Installationsstrategie: %DEP_INSTALL_METHOD%
    >> "%DEBUG_LOG%" echo [INFO] Dependency-Quelle: %DEP_INSTALL_SOURCE%
    "%RUNNER_PATH%" -m pip install -r "%PROJECT_DIR%requirements.txt"
    if errorlevel 1 (
        echo [FEHLER] Installation aus requirements.txt fehlgeschlagen.
        >> "%DEBUG_LOG%" echo [FEHLER] requirements.txt Installation fehlgeschlagen.
        exit /b 1
    )
    exit /b 0
)

if exist "%PROJECT_DIR%pyproject.toml" (
    set "DEP_INSTALL_SOURCE=%PROJECT_DIR%pyproject.toml"
    set "DEP_INSTALL_METHOD=pip install ."
    echo [INFO] Abhaengigkeitsquelle erkannt: pyproject.toml
    echo        "%DEP_INSTALL_SOURCE%"
    echo [INFO] Installationsstrategie: %DEP_INSTALL_METHOD%
    echo [INFO] Das Projekt wird ueber den Projektordner installiert.
    >> "%DEBUG_LOG%" echo [INFO] Dependency-Quelle: %DEP_INSTALL_SOURCE%
    "%RUNNER_PATH%" -m pip install .
    if errorlevel 1 (
        echo [FEHLER] Installation ueber pyproject.toml / pip install . fehlgeschlagen.
        >> "%DEBUG_LOG%" echo [FEHLER] pip install . fehlgeschlagen.
        exit /b 1
    )
    exit /b 0
)

set "DEP_INSTALL_SOURCE=none"
set "DEP_INSTALL_METHOD=only pyinstaller"
echo [INFO] Keine requirements.txt und kein pyproject.toml gefunden.
echo [INFO] Installationsstrategie: nur PyInstaller in der temporaeren .venv.
echo [INFO] Falls weitere Pakete benoetigt werden, bitte requirements.txt anlegen oder pyproject.toml korrekt konfigurieren.
>> "%DEBUG_LOG%" echo [INFO] Keine Projektabhaengigkeiten erkannt.
exit /b 0

:prepare_clean_build
echo [INFO] Bereite sauberen Build vor...
>> "%DEBUG_LOG%" echo [INFO] Bereite sauberen Build vor.

if exist "%DIST_DIR%" (
    echo [INFO] Loesche alten dist-Ordner:
    echo        "%DIST_DIR%"
    rd /s /q "%DIST_DIR%"
    if exist "%DIST_DIR%" (
        echo [FEHLER] dist-Ordner konnte nicht geloescht werden.
        >> "%DEBUG_LOG%" echo [FEHLER] dist konnte nicht geloescht werden: %DIST_DIR%
        exit /b 1
    )
) else (
    echo [INFO] Kein vorhandener dist-Ordner gefunden.
)

if exist "%BUILD_DIR%" (
    echo [INFO] Loesche alten build-Ordner:
    echo        "%BUILD_DIR%"
    rd /s /q "%BUILD_DIR%"
    if exist "%BUILD_DIR%" (
        echo [FEHLER] build-Ordner konnte nicht geloescht werden.
        >> "%DEBUG_LOG%" echo [FEHLER] build konnte nicht geloescht werden: %BUILD_DIR%
        exit /b 1
    )
) else (
    echo [INFO] Kein vorhandener build-Ordner gefunden.
)

exit /b 0

:invoke_pyinstaller
if "%RUNNER_KIND%"=="pyinstaller" (
    set "LAST_COMMAND=pyinstaller %*"
    echo [INFO] Starte: !LAST_COMMAND!
    >> "%DEBUG_LOG%" echo [INFO] Befehl: !LAST_COMMAND!
    pyinstaller %*
    set "CMD_EXIT=!errorlevel!"
    >> "%DEBUG_LOG%" echo [DEBUG] Befehl Errorlevel: !CMD_EXIT!
    exit /b !CMD_EXIT!
)
if "%RUNNER_KIND%"=="py" (
    set "LAST_COMMAND=py -m PyInstaller %*"
    echo [INFO] Starte: !LAST_COMMAND!
    >> "%DEBUG_LOG%" echo [INFO] Befehl: !LAST_COMMAND!
    py -m PyInstaller %*
    set "CMD_EXIT=!errorlevel!"
    >> "%DEBUG_LOG%" echo [DEBUG] Befehl Errorlevel: !CMD_EXIT!
    exit /b !CMD_EXIT!
)
if "%RUNNER_KIND%"=="python" (
    set "LAST_COMMAND="%RUNNER_PATH%" -m PyInstaller %*"
    echo [INFO] Starte: !LAST_COMMAND!
    >> "%DEBUG_LOG%" echo [INFO] Befehl: !LAST_COMMAND!
    "%RUNNER_PATH%" -m PyInstaller %*
    set "CMD_EXIT=!errorlevel!"
    >> "%DEBUG_LOG%" echo [DEBUG] Befehl Errorlevel: !CMD_EXIT!
    exit /b !CMD_EXIT!
)

echo [FEHLER] Kein gueltiger Runner gesetzt.
>> "%DEBUG_LOG%" echo [FEHLER] Kein gueltiger Runner gesetzt.
exit /b 1

:resolve_output
set "FINAL_ARTIFACT="
set "FOUND_EXE_COUNT=0"

if not exist "%DIST_DIR%" (
    echo [FEHLER] dist-Ordner wurde nach dem Build nicht gefunden:
    echo          "%DIST_DIR%"
    >> "%DEBUG_LOG%" echo [FEHLER] dist nach Build nicht gefunden: %DIST_DIR%
    exit /b 1
)

for /r "%DIST_DIR%" %%F in (*.exe) do (
    if exist "%%~fF" (
        set /a FOUND_EXE_COUNT+=1
        set "FOUND_EXE_!FOUND_EXE_COUNT!=%%~fF"
    )
)
>> "%DEBUG_LOG%" echo [DEBUG] Gefundene EXE-Anzahl: !FOUND_EXE_COUNT!

if !FOUND_EXE_COUNT! EQU 0 (
    echo [FEHLER] Keine EXE-Datei im dist-Ordner gefunden.
    echo          "%DIST_DIR%"
    >> "%DEBUG_LOG%" echo [FEHLER] Keine EXE-Datei in dist gefunden.
    exit /b 1
)

if !FOUND_EXE_COUNT! EQU 1 (
    set "FINAL_ARTIFACT=!FOUND_EXE_1!"
    echo [INFO] Eine EXE-Datei gefunden:
    echo        "!FOUND_EXE_1!"
    >> "%DEBUG_LOG%" echo [INFO] Finale EXE: !FOUND_EXE_1!
    exit /b 0
)

echo [INFO] Mehrere EXE-Dateien im dist-Ordner gefunden:
for /L %%N in (1,1,!FOUND_EXE_COUNT!) do (
    for %%F in ("!FOUND_EXE_%%N!") do echo   [%%N] %%~fF
)

:exe_prompt
set "EXE_CHOICE="
set /p "EXE_CHOICE=Welche EXE soll ins Projektverzeichnis kopiert werden? [1-!FOUND_EXE_COUNT!]: "
if not defined EXE_CHOICE set "EXE_CHOICE=1"

set "FINAL_ARTIFACT="
for /L %%N in (1,1,!FOUND_EXE_COUNT!) do (
    if "!EXE_CHOICE!"=="%%N" set "FINAL_ARTIFACT=!FOUND_EXE_%%N!"
)

if not defined FINAL_ARTIFACT (
    echo [FEHLER] Ungueltige Auswahl.
    >> "%DEBUG_LOG%" echo [FEHLER] Ungueltige EXE-Auswahl: !EXE_CHOICE!
    goto :exe_prompt
)

echo [INFO] Ausgewaehlte EXE:
echo        "!FINAL_ARTIFACT!"
>> "%DEBUG_LOG%" echo [INFO] Ausgewaehlte EXE: !FINAL_ARTIFACT!
exit /b 0

:copy_final_artifact_to_project
if not defined FINAL_ARTIFACT (
    echo [FEHLER] Kein finales Artefakt gesetzt.
    >> "%DEBUG_LOG%" echo [FEHLER] FINAL_ARTIFACT ist leer.
    exit /b 1
)

if not exist "%FINAL_ARTIFACT%" (
    echo [FEHLER] Finale EXE nicht gefunden:
    echo          "%FINAL_ARTIFACT%"
    >> "%DEBUG_LOG%" echo [FEHLER] Finale EXE nicht gefunden: %FINAL_ARTIFACT%
    exit /b 1
)

for %%F in ("%FINAL_ARTIFACT%") do (
    set "COPIED_ARTIFACT=%PROJECT_DIR%%%~nxF"
)

echo [INFO] Kopiere neue EXE ins Projektverzeichnis:
echo        "%COPIED_ARTIFACT%"
>> "%DEBUG_LOG%" echo [INFO] Kopiere EXE nach: %COPIED_ARTIFACT%
copy /y "%FINAL_ARTIFACT%" "%COPIED_ARTIFACT%" >nul
if errorlevel 1 (
    echo [FEHLER] Kopieren der neuen EXE fehlgeschlagen.
    >> "%DEBUG_LOG%" echo [FEHLER] Kopieren der EXE fehlgeschlagen.
    exit /b 1
)

exit /b 0

:cleanup_output_dirs
echo [INFO] Raeume Build-Ausgabe auf...
>> "%DEBUG_LOG%" echo [INFO] Build-Ausgabe wird aufgeraeumt.

if exist "%DIST_DIR%" (
    echo [INFO] Loesche dist-Ordner nach dem Kopieren:
    echo        "%DIST_DIR%"
    rd /s /q "%DIST_DIR%"
    if exist "%DIST_DIR%" (
        echo [FEHLER] dist-Ordner konnte nach dem Kopieren nicht geloescht werden.
        >> "%DEBUG_LOG%" echo [FEHLER] dist konnte nach Build nicht geloescht werden.
        exit /b 1
    )
) else (
    echo [INFO] dist-Ordner ist bereits entfernt.
)

if exist "%BUILD_DIR%" (
    echo [INFO] Loesche build-Ordner nach dem Kopieren:
    echo        "%BUILD_DIR%"
    rd /s /q "%BUILD_DIR%"
    if exist "%BUILD_DIR%" (
        echo [FEHLER] build-Ordner konnte nach dem Kopieren nicht geloescht werden.
        >> "%DEBUG_LOG%" echo [FEHLER] build konnte nach Build nicht geloescht werden.
        exit /b 1
    )
) else (
    echo [INFO] build-Ordner ist bereits entfernt.
)

exit /b 0

:cleanup_temp_venv
if not "%TEMP_VENV_CREATED%"=="1" exit /b 0

if exist "%TEMP_VENV_PATH%" (
    echo [INFO] Loesche temporaere .venv:
    echo        "%TEMP_VENV_PATH%"
    >> "%DEBUG_LOG%" echo [INFO] Loesche temporaere .venv: %TEMP_VENV_PATH%
    rd /s /q "%TEMP_VENV_PATH%"
    if exist "%TEMP_VENV_PATH%" (
        echo [FEHLER] Temporaere .venv konnte nicht geloescht werden.
        >> "%DEBUG_LOG%" echo [FEHLER] Temporaere .venv konnte nicht geloescht werden.
        exit /b 1
    )
)

exit /b 0

:fail
set "LAST_ERRORLEVEL=!errorlevel!"
if not defined FAIL_REASON set "FAIL_REASON=Unbekannter Fehler"
>> "%DEBUG_LOG%" echo [FAIL] Schritt: %LAST_STEP%
>> "%DEBUG_LOG%" echo [FAIL] Grund: %FAIL_REASON%
>> "%DEBUG_LOG%" echo [FAIL] Letzter Befehl: %LAST_COMMAND%
>> "%DEBUG_LOG%" echo [FAIL] Errorlevel: !LAST_ERRORLEVEL!

call :cleanup_temp_venv >nul 2>nul

echo.
echo ==========================================
echo [FEHLER] Build abgebrochen.
echo [FEHLER] Schritt: %LAST_STEP%
echo [FEHLER] Grund : %FAIL_REASON%
if defined LAST_COMMAND echo [DEBUG ] Letzter Befehl: %LAST_COMMAND%
if defined LAST_ERRORLEVEL echo [DEBUG ] Errorlevel    : !LAST_ERRORLEVEL!
echo [DEBUG ] Logdatei      : %DEBUG_LOG%
echo ==========================================

echo.
echo [HINWEIS] Das Fenster bleibt wegen des Fehlers offen.
if "%PAUSE_ON_ERROR%"=="1" pause
popd >nul 2>nul
endlocal
exit /b 1

:done
popd >nul 2>nul
endlocal
exit /b 0
