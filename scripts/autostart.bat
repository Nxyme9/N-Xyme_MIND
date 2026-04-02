@echo off
REM N-Xyme Catalyst Auto-Start
REM Place this file in shell:startup to auto-start on boot

echo Starting N-Xyme Catalyst services...

REM Start PM2 daemon and restore processes
call pm2 resurrect

REM Wait for services to initialize
timeout /t 5 /nobreak > nul

echo N-Xyme Catalyst services started.
