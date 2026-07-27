@echo off
REM ============================================================
REM  NovelForge - double-click this file to start writing.
REM
REM  This launches the full application. Everything works here:
REM  creating novels, writing, the map maker, the corkboard, the
REM  outline, settings, compiling and backups.
REM
REM  (The web redesign is unfinished and lives behind --web.
REM   Do not use it for real writing yet.)
REM ============================================================
setlocal

set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
set "PYW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"

REM Fall back to whatever Python is on PATH.
if not exist "%PY%" set "PY=python"
if not exist "%PYW%" set "PYW=%PY%"

cd /d "%~dp0"

REM pythonw.exe launches with no console window behind the app.
if exist "%PYW%" (
    start "" "%PYW%" -m novelforge
) else (
    "%PY%" -m novelforge
    if errorlevel 1 (
        echo.
        echo NovelForge could not start. The error is above.
        pause
    )
)

endlocal
