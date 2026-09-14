@echo off
REM ──────────────────────────────────────────────────────────────
REM  Rostam — ATT&CK Kill-Chain Telemetry Generator
REM  Windows bootstrap: ensures Python 3 + PyYAML, then launches the tool.
REM ──────────────────────────────────────────────────────────────
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM ── Find Python 3 ─────────────────────────────────────────────

set "PY="

where python >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%v in ('python -c "import sys; print(sys.version_info[0])" 2^>nul') do (
        if "%%v"=="3" set "PY=python"
    )
)

if not defined PY (
    where python3 >nul 2>&1
    if %errorlevel%==0 set "PY=python3"
)

if not defined PY (
    REM Check common install locations
    if exist "%LOCALAPPDATA%\Programs\Python\Python3*\python.exe" (
        for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do set "PY=%%d\python.exe"
    )
)

if not defined PY (
    echo [*] Python 3 not found.
    echo.
    set /p "INSTALL=  Install Python 3 now? [y/N] > "
    if /i "!INSTALL!"=="y" (
        call :install_python
    ) else (
        echo [!] Python 3 is required. Install from https://www.python.org/downloads/
        exit /b 1
    )
)

REM Re-check after install
if not defined PY (
    where python >nul 2>&1
    if %errorlevel%==0 (
        for /f "tokens=*" %%v in ('python -c "import sys; print(sys.version_info[0])" 2^>nul') do (
            if "%%v"=="3" set "PY=python"
        )
    )
)

if not defined PY (
    echo [!] Python 3 installation failed. Install manually from https://www.python.org/downloads/
    exit /b 1
)

for /f "tokens=*" %%v in ('%PY% --version 2^>^&1') do echo [+] %%v

REM ── Check PyYAML ──────────────────────────────────────────────

%PY% -c "import yaml" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Installing PyYAML...
    %PY% -m pip install pyyaml -q >nul 2>&1
    if %errorlevel% neq 0 (
        pip install pyyaml -q >nul 2>&1
    )
    %PY% -c "import yaml" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [!] Failed to install PyYAML. Run: pip install pyyaml
        exit /b 1
    )
)
echo [+] PyYAML available.

REM ── Create logs dir ───────────────────────────────────────────

if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"

REM ── Launch ────────────────────────────────────────────────────

%PY% "%SCRIPT_DIR%attack_sim.py"
exit /b %errorlevel%

REM ──────────────────────────────────────────────────────────────
REM  Python installer subroutine
REM ──────────────────────────────────────────────────────────────
:install_python
echo [*] Downloading Python installer...

set "INSTALLER=%TEMP%\python_installer.exe"
set "PY_URL=https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"

REM Try PowerShell download
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%INSTALLER%'" >nul 2>&1
if %errorlevel% neq 0 (
    REM Try certutil
    certutil -urlcache -split -f "%PY_URL%" "%INSTALLER%" >nul 2>&1
)

if not exist "%INSTALLER%" (
    echo [!] Download failed. Install Python 3 manually from https://www.python.org/downloads/
    exit /b 1
)

echo [*] Running installer (InstallAllUsers=0, PrependPath=1)...
"%INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1

REM Refresh PATH
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

del "%INSTALLER%" >nul 2>&1

where python >nul 2>&1
if %errorlevel%==0 (
    set "PY=python"
    echo [+] Python installed.
) else (
    echo [!] Python installed but not in PATH. You may need to restart this terminal.
    exit /b 1
)
goto :eof
