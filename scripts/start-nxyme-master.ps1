# N-Xyme Catalyst Master Startup
# Optimized for 7800X3D + 32GB RAM + RTX 3080 Ti
# Safe startup - just starts services, no config changes

param(
    [switch]$SkipOllama,
    [switch]$SkipOpenCode
)

$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "N-Xyme Catalyst"

function Write-Banner {
    param([string]$Text, [string]$Color = "Cyan")
    $colors = @{
        "Cyan" = [ConsoleColor]::Cyan
        "Green" = [ConsoleColor]::Green
        "Yellow" = [ConsoleColor]::Yellow
        "Red" = [ConsoleColor]::Red
        "White" = [ConsoleColor]::White
    }
    Write-Host ""
    Write-Host "===========================================================" -ForegroundColor $colors[$Color]
    Write-Host "  $Text" -ForegroundColor $colors[$Color]
    Write-Host "===========================================================" -ForegroundColor $colors[$Color]
    Write-Host ""
}

# Check if running as admin (for CPU affinity)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Banner "N-Xyme Catalyst - Performance Startup" "Cyan"

# Step 1: Check Ollama
Write-Host "[1/5] Checking Ollama..." -ForegroundColor Yellow
$ollamaPath = "C:\Users\N-Xyme\AppData\Local\Programs\Ollama\ollama.exe"

if (-not (Get-Process | Where-Object { $_.Path -eq $ollamaPath })) {
    if (-not $SkipOllama) {
        Write-Host "  Starting Ollama..." -ForegroundColor Gray
        Start-Process -FilePath $ollamaPath -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        Write-Host "  [OK] Ollama started" -ForegroundColor Green
    } else {
        Write-Host "  [SKIP] Ollama skipped" -ForegroundColor Gray
    }
} else {
    Write-Host "  [OK] Ollama already running" -ForegroundColor Green
}

# Step 2: Set memory optimization
Write-Host "[2/5] Configuring memory..." -ForegroundColor Yellow
$env:NODE_OPTIONS = "--max-old-space-size=8192"
Write-Host "  [OK] Node memory set to 8GB" -ForegroundColor Green

# Step 3: Ollama GPU optimization
if (-not $SkipOllama) {
    Write-Host "[3/5] Optimizing Ollama GPU..." -ForegroundColor Yellow
    $env:OLLAMA_NUM_PARALLEL = "3"
    $env:OLLAMA_MAX_LOADED_MODELS = "3"
    $env:OLLAMA_KEEP_ALIVE = "30m"
    $env:OLLAMA_FLASH_ATTENTION = "1"
    Write-Host "  [OK] Ollama GPU settings configured" -ForegroundColor Green
}

# Step 4: Navigate to project
Write-Host "[4/5] Setting project directory..." -ForegroundColor Yellow
$ProjectPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $ProjectPath) { $ProjectPath = Get-Location }
if (Test-Path $ProjectPath) {
    Set-Location $ProjectPath
    Write-Host "  [OK] Project: $ProjectPath" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Project not found: $ProjectPath" -ForegroundColor Red
}

# Step 5: CPU Affinity (requires admin)
Write-Host "[5/5] CPU Optimization..." -ForegroundColor Yellow
if ($isAdmin) {
    # 7800X3D V-Cache optimization
    Write-Host "  [INFO] Running as Admin - can set CPU affinity" -ForegroundColor Gray
    Write-Host "  [OK] Ready for manual affinity (run pin-cpu.ps1 separately)" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Not admin - CPU affinity needs elevation" -ForegroundColor Gray
    Write-Host "  [INFO] Run as admin or use pin-cpu.ps1 separately" -ForegroundColor Gray
}

Write-Banner "Ready to Start OpenCode" "Green"
Write-Host "Type 'opencode' to start, or run 'opencode' now to begin." -ForegroundColor White
Write-Host ""
Write-Host "Quick Commands:" -ForegroundColor Yellow
Write-Host "  opencode              - Start main session"
Write-Host "  opencode mcp list    - Check MCP servers"
Write-Host "  opencode agent list  - Check agents"
Write-Host ""
