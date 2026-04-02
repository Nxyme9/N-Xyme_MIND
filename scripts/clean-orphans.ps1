<#
.SYNOPSIS
    Cleans up orphaned OpenCode sessions spawned by plan/Prometheus/Sisyphus.

.DESCRIPTION
    Deletes sessions with fewer than the configured message threshold that were
    spawned by sub-agents. The current session is always protected from deletion.

    Supports dry-run mode (-DryRun) and WhatIf/Confirm via ShouldProcess.
    Session IDs to delete can be provided via a JSON config file or the built-in
    default list.

.PARAMETER DryRun
    Preview which sessions would be deleted without actually deleting them.

.PARAMETER ConfigPath
    Path to a JSON file containing an array of session IDs to delete.
    If omitted, uses the built-in default list.

.PARAMETER CurrentSession
    Session ID to protect from deletion (the running session).
    Default: ses_2fbd4f081ffeDgxe7pRr7nmgE4

.EXAMPLE
    .\clean-orphans.ps1 -DryRun
    Preview which sessions would be deleted.

.EXAMPLE
    .\clean-orphans.ps1 -Confirm:$false
    Delete orphans without interactive confirmation.

.EXAMPLE
    .\clean-orphans.ps1 -ConfigPath .\.sisyphus\orphan-ids.json
    Delete sessions listed in a custom config file.

.OUTPUTS
    None. Writes status messages and appends to .sisyphus/orphan-cleanup.log.
#>

[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
param(
    [switch]$DryRun,
    [string]$ConfigPath,
    [string]$CurrentSession = "ses_2fbd4f081ffeDgxe7pRr7nmgE4"
)

Set-StrictMode -Version Latest

# --- Default orphaned session IDs ---
$defaultOrphanedSessions = @(
    "ses_2fbd37c74ffeFC2giU0noauVD3",
    "ses_2fbd31d23ffe8bpIWUzpRfXa08",
    "ses_2fbd2dbb1ffe7g9kKGvmxnyEV3",
    "ses_2fbd2b1a1ffee1YSmluBzZsmlR",
    "ses_2fbd27d20ffeDIsOx15VVBVZ0l",
    "ses_2fbcabbb4ffe54w3i7BmCKVynK",
    "ses_2fbca5f4effelRbJzZePoqLCTg",
    "ses_2fbc9500dffeW8rhQ54dczA6R9",
    "ses_2fbc838daffezdbdKcZe7XlGaa",
    "ses_2fbc693cdffe2kmvZ3Y2mGgc1P",
    "ses_2fbc61a61ffe0uJUTKCbtqqfzL",
    "ses_2fbc56632ffeg3B4IS6wnSt5px",
    "ses_2fbc4a696ffeT8JyW4DmtKIqBB"
)

# --- Load session IDs from config or defaults ---
if ($ConfigPath -and (Test-Path $ConfigPath)) {
    try {
        $orphanedSessions = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
        Write-Host "Loaded $($orphanedSessions.Count) session IDs from $ConfigPath" -ForegroundColor DarkGray
    } catch {
        Write-Warning "Failed to parse config '$ConfigPath': $_. Using defaults."
        $orphanedSessions = $defaultOrphanedSessions
    }
} else {
    $orphanedSessions = $defaultOrphanedSessions
}

# --- Header ---
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host "  ORPHAN CLEANUP - $($orphanedSessions.Count) sessions to delete" -ForegroundColor Cyan
Write-Host "===============================================================" -ForegroundColor Cyan

# --- Dry run ---
if ($DryRun) {
    Write-Host "`n[DRY RUN] Would delete these sessions:" -ForegroundColor Yellow
    foreach ($sessionId in $orphanedSessions) {
        Write-Host "  - $sessionId" -ForegroundColor Gray
    }
    Write-Host "`nRun without -DryRun to actually delete." -ForegroundColor Yellow
    exit 0
}

# --- Safety info ---
Write-Host "`nSAFETY CHECK:" -ForegroundColor Yellow
Write-Host "  Current session (PROTECTED): $CurrentSession" -ForegroundColor Green
Write-Host "  Sessions to delete: $($orphanedSessions.Count)" -ForegroundColor Red

# --- Deletion loop ---
$deletedCount = 0
foreach ($sessionId in $orphanedSessions) {
    if ($sessionId -eq $CurrentSession) {
        Write-Host "SKIP (current session): $sessionId" -ForegroundColor Yellow
        continue
    }

    if (-not $PSCmdlet.ShouldProcess($sessionId, "Delete orphaned session")) {
        continue
    }

    try {
        if (Get-Command opencode -ErrorAction SilentlyContinue) {
            $result = opencode session delete --session-id $sessionId --confirm 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "DELETED: $sessionId" -ForegroundColor Green
                $deletedCount++
            } else {
                Write-Host "FAILED: $sessionId - $result" -ForegroundColor Red
            }
        } else {
            $sessionDir = Join-Path $Env:APPDATA "opencode\sessions\$sessionId"
            if (Test-Path $sessionDir) {
                Remove-Item -Path $sessionDir -Recurse -Force
                Write-Host "DELETED (direct): $sessionId" -ForegroundColor Green
                $deletedCount++
            } else {
                Write-Host "NOT FOUND: $sessionId" -ForegroundColor Gray
            }
        }
    } catch {
        Write-Host "ERROR: $sessionId - $_" -ForegroundColor Red
    }
}

# --- Summary ---
Write-Host "`n===============================================================" -ForegroundColor Cyan
Write-Host "  CLEANUP COMPLETE - Deleted $deletedCount of $($orphanedSessions.Count) sessions" -ForegroundColor Cyan
Write-Host "===============================================================" -ForegroundColor Cyan

# --- Log cleanup ---
$logDir = Join-Path -Path $PSScriptRoot -ChildPath "..\.sisyphus"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logPath = Join-Path -Path $logDir -ChildPath "orphan-cleanup.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logEntry = "$timestamp - Deleted $deletedCount orphaned sessions"
Add-Content -Path $logPath -Value $logEntry
