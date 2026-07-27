@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%.venv"
set "PYTHON=%VENV_DIR%\Scripts\python.exe"
set "PYTHONW=%VENV_DIR%\Scripts\pythonw.exe"

cd /d "%PROJECT_DIR%" || goto :project_dir_failed

if exist "%PYTHON%" goto :venv_ready
call :create_venv
if errorlevel 1 goto :setup_failed

:venv_ready
"%PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto :wrong_python

"%PYTHON%" -c "import PySide6" >nul 2>&1
if not errorlevel 1 goto :dependencies_ready
call :install_runtime
if errorlevel 1 goto :setup_failed

:dependencies_ready
if /i "%~1"=="--setup-only" goto :setup_complete

start "Toolbox" /D "%PROJECT_DIR%" "%PYTHONW%" "%PROJECT_DIR%main.py"
if errorlevel 1 goto :start_failed
exit /b 0

:create_venv
echo Creating .venv with Python 3.11...
py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto :python_missing

py -3.11 -m venv "%VENV_DIR%"
if errorlevel 1 exit /b 1
call :install_runtime
exit /b %ERRORLEVEL%

:install_runtime
echo Installing Toolbox dependencies in .venv...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"%PYTHON%" -m pip install -r "%PROJECT_DIR%requirements.txt"
exit /b %ERRORLEVEL%

:python_missing
echo [ERROR] Python 3.11 was not found.
echo Install Python 3.11 including the Windows Python Launcher and try again.
exit /b 1

:wrong_python
echo [ERROR] The existing .venv does not use Python 3.11.
echo Remove the .venv directory and run this launcher again.
goto :setup_failed

:setup_complete
echo Python 3.11 environment is ready: %PYTHON%
exit /b 0

:project_dir_failed
echo [ERROR] Could not open the project directory: %PROJECT_DIR%
exit /b 1

:start_failed
echo [ERROR] The Toolbox process could not be started.
goto :setup_failed

:setup_failed
echo.
echo [ERROR] The Python 3.11 environment could not be prepared or started.
echo Review the messages above and run this launcher again.
echo.
pause
exit /b 1
