# N-Xyme Catalyst Auto-Start Script
# Run on Windows boot to start all services
# Schedule with Task Scheduler or add to Startup folder

$ErrorActionPreference = "Continue"
$ProjectRoot = "D:\01_CODING\00_N-Xyme_CATALYST"
$LogPath = "$ProjectRoot\logs\autostart.log"

# Ensure log directory exists
$LogDir = Split-Path $LogPath -Parent
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

function Write-Log {
    param($Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Out-File -Append -FilePath $LogPath
}

Write-Log "=== N-Xyme Catalyst Auto-Start Started ==="

# Wait for network
Start-Sleep -Seconds 5

# 1. Start PM2 services (MCP servers)
Write-Log "Starting PM2 services..."
pm2 resurrect
Start-Sleep -Seconds 3
pm2 status
Write-Log "PM2 services started"

# 2. Start Auto-Capture Service (Python)
Write-Log "Starting Auto-Capture Service..."
$AutoCaptureProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*auto-capture*" }
if (-not $AutoCaptureProcess) {
    Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "packages.auto-capture.src.main:app", "--host", "0.0.0.0", "--port", "5003" -WorkingDirectory $ProjectRoot -WindowStyle Hidden
    Write-Log "Auto-Capture Service started on port 5003"
} else {
    Write-Log "Auto-Capture Service already running"
}

# 3. Start Session Archiver (if exists)
Write-Log "Checking Session Archiver..."
$SessionArchiverProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*session-archiver*" }
if (-not $SessionArchiverProcess) {
    if (Test-Path "$ProjectRoot\packages\chat-extractor\run_archiver.py") {
        Start-Process -FilePath "python" -ArgumentList "$ProjectRoot\packages\chat-extractor\run_archiver.py" -WorkingDirectory $ProjectRoot -WindowStyle Hidden
        Write-Log "Session Archiver started"
    } else {
        Write-Log "Session Archiver not found (optional)"
    }
} else {
    Write-Log "Session Archiver already running"
}

# 4. Start Jarvis Hub (optional - uncomment if you want it auto-started)
# Write-Log "Starting Jarvis Hub..."
# Start-Process -FilePath "python" -ArgumentList "scripts\nxyme-hub.py" -WorkingDirectory $ProjectRoot -WindowStyle Hidden
# Write-Log "Jarvis Hub started"

# 5. Start Heartbeat Monitor
Write-Log "Starting Heartbeat Monitor..."
$HeartbeatProcess = Get-Process -Name "powershell" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*heartbeat-monitor*" }
if (-not $HeartbeatProcess) {
    Start-Process -FilePath "powershell" -ArgumentList "-ExecutionPolicy", "Bypass", "-File", "$ProjectRoot\scripts\heartbeat-monitor.ps1" -WorkingDirectory $ProjectRoot -WindowStyle Normal
    Write-Log "Heartbeat Monitor started"
} else {
    Write-Log "Heartbeat Monitor already running"
}

Write-Log "=== Auto-Start Complete ==="
