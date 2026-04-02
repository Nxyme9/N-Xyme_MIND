#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Hardware + Software optimizer for developer workstation.
.DESCRIPTION
    Applies safe, industry-standard optimizations across CPU, RAM, GPU, Disk, Node.js, Git, NPM.
.PARAMETER DryRun
    Show what would be changed without making changes.
#>

[CmdletBinding()]
param([switch]$DryRun)

Set-StrictMode -Version Latest

$changes = @()

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  HARDWARE + SOFTWARE OPTIMIZER" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan

Write-Host ""; Write-Host "[1] CPU + POWER PLAN" -ForegroundColor Green
$currentPlan = (powercfg /getactivescheme 2>&1)
if ($currentPlan -match "Balanced|381b4222") {
    Write-Host "  Switching to High Performance..." -ForegroundColor Yellow
    if (-not $DryRun) { powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2>&1 | Out-Null; $changes += "Power plan: High Performance" }
} else { Write-Host "  Already optimized." -ForegroundColor Gray }
Write-Host "  Disabling CPU core parking..." -ForegroundColor Yellow
if (-not $DryRun) { powercfg /setacvalueindex scheme_current sub_processor CPMINCORES 100 2>&1 | Out-Null; powercfg /setactive scheme_current 2>&1 | Out-Null; $changes += "CPU core parking: Disabled" }

Write-Host ""; Write-Host "[2] RAM + MEMORY" -ForegroundColor Green
$memComp = Get-MMAgent | Select-Object -ExpandProperty MemoryCompression
if (-not $memComp) { Write-Host "  Enabling memory compression..." -ForegroundColor Yellow; if (-not $DryRun) { Enable-MMAgent -MemoryCompression 2>&1 | Out-Null; $changes += "Memory compression: Enabled" } }
else { Write-Host "  Memory compression already enabled." -ForegroundColor Gray }

Write-Host ""; Write-Host "[3] GPU - RTX 3080 Ti" -ForegroundColor Green
Write-Host "  Enabling GPU hardware scheduling..." -ForegroundColor Yellow
if (-not $DryRun) { Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" -Name "HwSchMode" -Value 2 -Type DWord -Force 2>&1 | Out-Null; $changes += "GPU hardware scheduling: Enabled" }

Write-Host ""; Write-Host "[4] DISK + FILESYSTEM" -ForegroundColor Green
Write-Host "  Disabling NTFS last access time..." -ForegroundColor Yellow
if (-not $DryRun) { fsutil behavior set disablelastaccess 1 2>&1 | Out-Null; $changes += "NTFS last access time: Disabled" }
Write-Host "  Disabling 8.3 short filenames..." -ForegroundColor Yellow
if (-not $DryRun) { fsutil behavior set disable8dot3 1 2>&1 | Out-Null; $changes += "NTFS 8.3 names: Disabled" }

Write-Host ""; Write-Host "[5] NODE.JS + V8" -ForegroundColor Green
$nodeCacheDir = "C:\Users\N-Xyme\.node_compile_cache"
Write-Host "  Enabling compile cache..." -ForegroundColor Yellow
if (-not $DryRun) { [System.Environment]::SetEnvironmentVariable("NODE_COMPILE_CACHE", $nodeCacheDir, "User"); $changes += "NODE_COMPILE_CACHE: Enabled" }
Write-Host "  Setting NODE_OPTIONS..." -ForegroundColor Yellow
if (-not $DryRun) { [System.Environment]::SetEnvironmentVariable("NODE_OPTIONS", "--max-old-space-size=8192", "User"); $changes += "NODE_OPTIONS: 8GB heap" }
if (-not $DryRun -and -not (Test-Path $nodeCacheDir)) { New-Item -ItemType Directory -Path $nodeCacheDir -Force | Out-Null; $changes += "Compile cache dir: Created" }

Write-Host ""; Write-Host "[6] GIT" -ForegroundColor Green
if (-not $DryRun) {
    git config --global core.fsmonitor true 2>&1 | Out-Null
    git config --global core.untrackedcache true 2>&1 | Out-Null
    git config --global core.preloadindex true 2>&1 | Out-Null
    git config --global pack.threads 16 2>&1 | Out-Null
    git config --global pack.deltaCacheSize "512m" 2>&1 | Out-Null
    $changes += "Git fsmonitor: Enabled"; $changes += "Git parallel: 16 threads"
} else { Write-Host "  Would enable fsmonitor, untracked cache, parallel pack" -ForegroundColor Gray }

Write-Host ""; Write-Host "[7] NPM" -ForegroundColor Green
if (-not $DryRun) {
    npm config set prefer-offline true 2>&1 | Out-Null
    npm config set cache-max 86400 2>&1 | Out-Null
    npm config set maxsockets 16 2>&1 | Out-Null
    $changes += "NPM prefer-offline: true"; $changes += "NPM cache: 24h, 16 sockets"
} else { Write-Host "  Would set prefer-offline, cache-max=24h, maxsockets=16" -ForegroundColor Gray }

Write-Host ""; Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
if ($changes.Count -eq 0) { Write-Host "  Already optimized!" -ForegroundColor Green }
else { $changes | ForEach-Object { Write-Host "  * $_" -ForegroundColor Gray } }
Write-Host ""; Write-Host "RESTART required for system-level changes." -ForegroundColor Yellow
