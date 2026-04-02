@echo off
title Dictation Tool
cd /d D:\01_CODING\00_N-Xyme_CATALYST

echo ========================================
echo   DICTATION TOOL
echo ========================================
echo.
echo Loading Whisper model (may take 10-20 seconds)...
echo.

python scripts\dictate.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo   ERROR - Script failed!
    echo ========================================
    echo.
    echo Press any key to see full Python path...
    pause
    where python
    echo.
    echo Try running manually:
    echo   python D:\01_CODING\00_N-Xyme_CATALYST\scripts\dictate.py
    echo.
)
pause
