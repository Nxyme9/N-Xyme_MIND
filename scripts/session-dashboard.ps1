<#
.SYNOPSIS
    Displays an OpenCode session dashboard with status indicators.

.DESCRIPTION
    Lists all OpenCode sessions with message counts, agent usage, and status
    indicators (Active/Stale/Orphaned). Imports shared functions from
    SessionHelpers.psm1 for status classification and agent formatting.

.EXAMPLE
    .\session-dashboard.ps1
    Show the session dashboard.

.OUTPUTS
    Formatted table with columns: ID, Messages, Agents, Status, Last Active
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest

# --- Import shared helpers ---
$helpersPath = Join-Path $PSScriptRoot "SessionHelpers.psm1"
if (Test-Path $helpersPath) {
    Import-Module $helpersPath -Force
} else {
    Write-Warning "SessionHelpers.psm1 not found at $helpersPath. Using inline fallbacks."
    # Inline fallbacks (should not normally execute)
    function Get-SessionStatus {
        param([int]$MessageCount, [datetime]$LastActive)
        if ($MessageCount -lt 5) { return "[ORPHAN]" }
        if ($LastActive) {
            $hours = ((Get-Date) - $LastActive).TotalHours
            if ($hours -gt 24) { return "[STALE>24h]" }
            elseif ($hours -gt 1) { return "[STALE]" }
        }
        return "[ACTIVE]"
    }
    function Format-Agents {
        param($Agents)
        if ($null -eq $Agents) { return "none" }
        if ($Agents -is [Array]) { return ($Agents -join ", ") }
        return $Agents.ToString()
    }
}

# --- Get session list ---
try {
    $sessionsJson = & opencode session list --format json 2>$null
} catch {
    Write-Error "Failed to execute 'opencode session list': $_"
    exit 1
}

if (-not $sessionsJson) {
    Write-Host "No sessions found. Ensure opencode CLI is available." -ForegroundColor Yellow
    exit 0
}

try {
    $sessions = $sessionsJson | ConvertFrom-Json
} catch {
    Write-Error "Failed to parse session list JSON: $_"
    exit 1
}

if (-not $sessions -or $sessions.Count -eq 0) {
    Write-Host "No sessions found." -ForegroundColor Yellow
    exit 0
}

# --- Build table ---
Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "  SESSION DASHBOARD" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan

$table = @()
foreach ($s in $sessions) {
    $lastActive = if ($s.last_message) { [datetime]$s.last_message } else { Get-Date }
    $status = Get-SessionStatus -MessageCount $s.message_count -LastActive $lastActive
    $agentsFormatted = Format-Agents -Agents $s.agents_used
    $agentsDisplay = if ($agentsFormatted) { $agentsFormatted.Substring(0, [Math]::Min(30, $agentsFormatted.Length)) } else { "" }

    $table += [PSCustomObject]@{
        "ID"          = if ($s.id) { $s.id.Substring(0, [Math]::Min(12, $s.id.Length)) + "..." } else { "unknown..." }
        "Messages"    = $s.message_count
        "Agents"      = $agentsDisplay
        "Status"      = $status
        "Last Active" = $lastActive.ToString("yyyy-MM-dd HH:mm")
    }
}

# Sort: Active first, then by message count descending
$table | Sort-Object @{E={if($_.Status -like "[ACTIVE]*") {0} elseif($_.Status -like "[STALE]*") {1} else {2}}}, Messages -Descending | Format-Table -AutoSize

# --- Summary ---
$activeCount = ($table | Where-Object { $_.Status -like "[ACTIVE]*" }).Count
$staleCount  = ($table | Where-Object { $_.Status -like "[STALE]*" }).Count
$orphanCount = ($table | Where-Object { $_.Status -like "[ORPHAN]*" }).Count

Write-Host "Summary: $activeCount active | $staleCount stale | $orphanCount orphaned | $($sessions.Count) total" -ForegroundColor Gray
Write-Host "===========================================================`n" -ForegroundColor Cyan
