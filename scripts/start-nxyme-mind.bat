@echo off
REM N-Xyme Mind Startup Script
REM Double-click this file to start all services

title N-Xyme Mind Startup

echo.
echo ========================================
echo   N-Xyme Mind Startup
echo ========================================
echo.

REM Get the directory of this batch file
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\.."

REM Run the Python startup script
python scripts\start-nxyme-mind.py

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred. Press any key to exit.
    pause >nul
)

exit /b %ERRORLEVEL%