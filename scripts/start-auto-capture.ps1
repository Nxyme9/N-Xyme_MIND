# Start Auto-Capture Service for N-Xyme Catalyst
# This script starts the auto-capture service locally (requires Python and dependencies).

$ErrorActionPreference = "Stop"

# Set the working directory to the project root
Set-Location (Split-Path $PSScriptRoot -Parent)

# Ensure the capture directory exists
$captureDir = "D:\00_CODING\captures"
if (-not (Test-Path $captureDir)) {
    New-Item -ItemType Directory -Path $captureDir | Out-Null
    Write-Host "Created capture directory: $captureDir"
}

# Activate virtual environment if exists (optional)
# .\venv\Scripts\Activate.ps1

# Start the service
Write-Host "Starting Auto-Capture Service on port 5003..."
Set-Location "packages\auto-capture\src"
python -m uvicorn main:app --host 0.0.0.0 --port 5003 --log-level info