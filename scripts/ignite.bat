@echo off
echo ========================================
echo N-XYME IGNITION - Starting All Systems
echo ========================================
echo.
echo Starting PM2 processes...
call pm2 resurrect
echo.
echo Starting GPU automation...
wscript.exe "D:\01_CODING\00_N-Xyme_CATALYST\scripts\ignite-background.vbs"
echo.
echo All systems started in background.
echo Check PM2 status: pm2 list
echo Check GPU status: python -m jarvis.gpu_dashboard
echo.
pause
