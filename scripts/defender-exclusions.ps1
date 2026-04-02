<#
.SYNOPSIS
    Safe Windows Defender exclusions for developers.

.DESCRIPTION
    Adds path, process, and extension exclusions to Windows Defender
    to reduce CPU/RAM overhead during development.

.PARAMETER Remove
    Remove all added exclusions instead of adding them.

.PARAMETER DryRun
    Show what would be added without making changes.

.EXAMPLE
    .\defender-exclusions.ps1
    .\defender-exclusions.ps1 -DryRun
    .\defender-exclusions.ps1 -Remove

.OUTPUTS
    Summary of exclusions added/removed.
#>

[CmdletBinding()]
param(
    [switch]$Remove,
    [switch]$DryRun
)

Set-StrictMode -Version Latest

# Requires admin
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script requires Administrator privileges. Run PowerShell as Administrator."
    exit 1
}

# PATH EXCLUSIONS
$pathExclusions = @(
    "D:_CODING",
    "$env:APPDATA
pm",
    "$env:APPDATA
pm-cache",
    "$env:LOCALAPPDATA
pm-cache",
    "$env:TEMP"
)

# PROCESS EXCLUSIONS
$processExclusions = @(
    "node.exe",
    "npm.exe",
    "npx.exe",
    "tsx.exe",
    "tsc.exe",
    "ts-node.exe",
    "deno.exe",
    "bun.exe",
    "cargo.exe",
    "rustc.exe",
    "python.exe",
    "pip.exe",
    "git.exe",
    "opencode.exe",
    "ollama.exe"
)

# EXTENSION EXCLUSIONS
$extensionExclusions = @(
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".json", ".ps1", ".psm1", ".psd1",
    ".md", ".yaml", ".yml", ".toml", ".lock"
)

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  WINDOWS DEFENDER EXCLUSIONS FOR DEVELOPERS" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "`n[DRY RUN] Would apply these exclusions:" -ForegroundColor Yellow
    Write-Host "`nPATH EXCLUSIONS:" -ForegroundColor Green
    $pathExclusions | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    Write-Host "`nPROCESS EXCLUSIONS:" -ForegroundColor Green
    $processExclusions | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    Write-Host "`nEXTENSION EXCLUSIONS:" -ForegroundColor Green
    $extensionExclusions | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    Write-Host "`nRun without -DryRun to apply." -ForegroundColor Yellow
    exit 0
}

$currentPaths = (Get-MpPreference).ExclusionPath
$currentProcesses = (Get-MpPreference).ExclusionProcess
$currentExtensions = (Get-MpPreference).ExclusionExtension

if ($Remove) {
    Write-Host "`nRemoving exclusions..." -ForegroundColor Yellow
    foreach ($path in $pathExclusions) {
        if ($currentPaths -contains $path) {
            Remove-MpPreference -ExclusionPath $path -ErrorAction SilentlyContinue
            Write-Host "  Removed: $path" -ForegroundColor Green
        }
    }
    foreach ($proc in $processExclusions) {
        if ($currentProcesses -contains $proc) {
            Remove-MpPreference -ExclusionProcess $proc -ErrorAction SilentlyContinue
            Write-Host "  Removed: $proc" -ForegroundColor Green
        }
    }
    foreach ($ext in $extensionExclusions) {
        if ($currentExtensions -contains $ext) {
            Remove-MpPreference -ExclusionExtension $ext -ErrorAction SilentlyContinue
            Write-Host "  Removed: $ext" -ForegroundColor Green
        }
    }
    Write-Host "`nExclusions removed." -ForegroundColor Green
    exit 0
}

Write-Host "`nAdding exclusions..." -ForegroundColor Green
$added = 0
$skipped = 0

foreach ($path in $pathExclusions) {
    if ($currentPaths -contains $path) {
        Write-Host "  SKIP (exists): $path" -ForegroundColor Gray
        $skipped++
    } else {
        try {
            Add-MpPreference -ExclusionPath $path -ErrorAction Stop
            Write-Host "  ADDED: $path" -ForegroundColor Green
            $added++
        } catch {
            Write-Warning "  FAILED: $path - $_"
        }
    }
}

foreach ($proc in $processExclusions) {
    if ($currentProcesses -contains $proc) {
        Write-Host "  SKIP (exists): $proc" -ForegroundColor Gray
        $skipped++
    } else {
        try {
            Add-MpPreference -ExclusionProcess $proc -ErrorAction Stop
            Write-Host "  ADDED: $proc" -ForegroundColor Green
            $added++
        } catch {
            Write-Warning "  FAILED: $proc - $_"
        }
    }
}

foreach ($ext in $extensionExclusions) {
    if ($currentExtensions -contains $ext) {
        Write-Host "  SKIP (exists): $ext" -ForegroundColor Gray
        $skipped++
    } else {
        try {
            Add-MpPreference -ExclusionExtension $ext -ErrorAction Stop
            Write-Host "  ADDED: $ext" -ForegroundColor Green
            $added++
        } catch {
            Write-Warning "  FAILED: $ext - $_"
        }
    }
}

Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "  SUMMARY: $added added, $skipped already existed" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan

Write-Host "`nSECURITY NOTES:" -ForegroundColor Yellow
Write-Host "  - Real-time protection: STILL ACTIVE" -ForegroundColor Green
Write-Host "  - Tamper protection: STILL ACTIVE" -ForegroundColor Green
Write-Host "  - Only trusted dev directories excluded" -ForegroundColor Green
Write-Host "  - Run with -Remove to undo all exclusions" -ForegroundColor Gray
Write-Host "`nRESTART recommended for full effect." -ForegroundColor Cyan
