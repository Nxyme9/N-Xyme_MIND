<#
.SYNOPSIS
    Detects orphaned OpenCode sessions and flags them for cleanup.

.DESCRIPTION
    Scans all OpenCode sessions and identifies orphans based on two criteria:
    1. Sessions older than 7 days with fewer than 5 messages
    2. Sessions spawned by Sisyphus/Prometheus sub-agents with fewer than 5 messages

    Runs at most once per day (checks log for last run timestamp).
    Does NOT auto-delete — only flags sessions for manual cleanup via '/clean-orphans'.

    Logs results to .sisyphus/orphan-policy.log.

.PARAMETER None
    This script takes no parameters.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File ./scripts/orphan-policy.ps1
    Runs the orphan policy check and displays flagged sessions.

.OUTPUTS
    Console output listing orphaned sessions with reasons.
    Log entries appended to .sisyphus/orphan-policy.log.
#>

[CmdletBinding()]
param()

# Ensure we have the opencode CLI available
if (-not (Get-Command opencode -ErrorAction SilentlyContinue)) {
    Write-Host "Error: 'opencode' command not found. Please ensure OpenCode CLI is installed and in PATH." -ForegroundColor Red
    exit 1
}

# Use built-in ConvertFrom-Json (no external dependency)
Set-StrictMode -Version Latest

# Configuration
$LOG_DIR = ".sisyphus"
$LOG_FILE = Join-Path $LOG_DIR "orphan-policy.log"
$MAX_AGE_DAYS = 7
$MAX_MESSAGES = 5

# Ensure log directory exists
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
}

function Write-Log {
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] $message"
    Add-Content -Path $LOG_FILE -Value $logEntry
}

function Test-AlreadyRunToday {
    if (-not (Test-Path $LOG_FILE)) {
        return $false
    }

    $lastRun = Get-Content $LOG_FILE -ErrorAction SilentlyContinue |
        Where-Object { $_ -match "^\[(\d{4}-\d{2}-\d{2})" } |
        ForEach-Object { [regex]::Match($_, "^\[(\d{4}-\d{2}-\d{2})").Groups[1].Value } |
        Sort-Object -Descending |
        Select-Object -First 1

    if (-not $lastRun) {
        return $false
    }

    $today = Get-Date -Format "yyyy-MM-dd"
    return ($lastRun -eq $today)
}

function Get-SessionList {
    try {
        $json = & opencode session list --format json 2>$null
    } catch {
        Write-Log "ERROR: Failed to list sessions: $_"
        return @()
    }
    if (-not $json) {
        return @()
    }
    try {
        $sessions = $json | ConvertFrom-Json
        return ,$sessions
    } catch {
        Write-Log "ERROR: Failed to parse session list JSON: $_"
        return @()
    }
}

function Get-SessionMessageCount {
    param([string]$sessionID)
    # Use a timeout approach - try to get export with a short timeout
    $job = Start-Job -ScriptBlock {
        param($sid)
        opencode export $sid 2>$null
    } -ArgumentList $sessionID

    # Wait for job with timeout (5 seconds per session)
    $completed = Wait-Job $job -Timeout 5
    if ($completed) {
        $exportJson = Receive-Job $job
        Remove-Job $job -Force

        if ($exportJson) {
            try {
                $data = $exportJson | ConvertFrom-Json
                $messages = $data["messages"]
                $messageCount = if ($messages) { $messages.Count } else { 0 }

                # Check for Sisyphus/Prometheus agents
                $agents = @()
                if ($messages) {
                    foreach ($msg in $messages) {
                        if ($msg["info"] -and $msg["info"]["agent"]) {
                            $agent = $msg["info"]["agent"]
                            if ($agent -and -not ($agents -contains $agent)) {
                                $agents += $agent
                            }
                        }
                    }
                }

                return @{
                    MessageCount = $messageCount
                    Agents = $agents
                }
            } catch {
                return $null
            }
        }
    } else {
        # Timeout - kill the job
        Stop-Job $job
        Remove-Job $job -Force
        return $null
    }
    return $null
}

function Format-Agents {
    param([array]$agentsArray)
    if (-not $agentsArray -or $agentsArray.Count -eq 0) { return "" }
    return ($agentsArray | ForEach-Object { $_.ToString() } | Where-Object { $_ -ne '' } ) -join ", "
}

# Check if already run today
if (Test-AlreadyRunToday) {
    Write-Host "Orphan policy already run today. Skipping." -ForegroundColor Gray
    exit 0
}

Write-Log "=== Orphan Policy Check Started ==="

# Get sessions
$sessions = Get-SessionList
if ($sessions.Count -eq 0) {
    Write-Log "No sessions found."
    Write-Host "No sessions found." -ForegroundColor Gray
    exit 0
}

Write-Log "Found $($sessions.Count) sessions. Analyzing..."

$orphanedSessions = @()
$processed = 0
$now = Get-Date
$cutoffDate = $now.AddDays(-$MAX_AGE_DAYS)

foreach ($s in $sessions) {
    $processed++
    Write-Progress -Activity "Analyzing sessions for orphan policy" -Status "$processed of $($sessions.Count)" -PercentComplete (($processed / $sessions.Count) * 100)

    $id = $s["id"]
    $title = $s["title"]
    $createdMs = $s["created"]

    # Calculate age from created timestamp (milliseconds since epoch)
    $createdAt = $null
    $ageDays = $null
    if ($createdMs) {
        $createdAt = [DateTimeOffset]::FromUnixTimeMilliseconds($createdMs).LocalDateTime
        $ageDays = [math]::Floor(($now - $createdAt).TotalDays)
    }

    # Skip sessions younger than MAX_AGE_DAYS (unless we need to check for spawn flag)
    # We'll check all sessions for spawn flag, but only export old ones for message count
    $needsExport = $false
    if ($ageDays -ne $null -and $ageDays -ge $MAX_AGE_DAYS) {
        $needsExport = $true
    }

    if ($needsExport) {
        # Export session to check message count and agents
        $details = Get-SessionMessageCount -sessionID $id

        if (-not $details) {
            # If we can't get details, flag as potential orphan
            $orphanedSessions += [pscustomobject]@{
                SessionID = $id
                Title = $title
                Messages = 0
                Agents = ""
                Age = "$ageDays days"
                Reason = "Failed to export session data"
            }
            Write-Log "FLAGGED: Session $id - Failed to export"
            continue
        }

        $messages = $details.MessageCount
        $agents = Format-Agents -agentsArray $details.Agents

        # Spawn check: treat Sisyphus/Prometheus as special sub-agent spawns
        $spawnFlag = $false
        if ($agents -and $agents -match "(?i)(Sisyphus|Prometheus)" -and $messages -lt 5) { $spawnFlag = $true }

        # Orphan condition: (older than 7 days AND < 5 messages) OR spawn flag
        $isOrphan = $false
        $reasons = @()

        if ($spawnFlag) {
            $isOrphan = $true
            $reasons += "Spawned by Sisyphus/Prometheus sub-agent"
        }

        if ($ageDays -ge $MAX_AGE_DAYS -and $messages -lt $MAX_MESSAGES) {
            $isOrphan = $true
            $reasons += "Older than $MAX_AGE_DAYS days with < $MAX_MESSAGES messages"
        }

        if ($isOrphan) {
            $orphanedSessions += [pscustomobject]@{
                SessionID = $id
                Title = $title
                Messages = $messages
                Agents = $agents
                Age = "$ageDays days"
                Reason = ($reasons -join "; ")
            }
            Write-Log "FLAGGED: Session $id - $($reasons -join '; ')"
        }
    }
}

Write-Progress -Activity "Analyzing sessions for orphan policy" -Completed

# Output results
if ($orphanedSessions.Count -gt 0) {
    Write-Host ""
    Write-Host "Found $($orphanedSessions.Count) orphaned sessions:" -ForegroundColor Yellow
    Write-Host ""

    $orphanedSessions | Select-Object SessionID, Title, Messages, Agents, Age, Reason | Format-Table -AutoSize

    Write-Host "Run '/clean-orphans' to archive these sessions." -ForegroundColor Cyan
    Write-Log "RESULT: Found $($orphanedSessions.Count) orphaned sessions flagged for cleanup"
} else {
    Write-Host "No orphaned sessions found." -ForegroundColor Green
    Write-Log "RESULT: No orphaned sessions found"
}

Write-Log "=== Orphan Policy Check Completed ==="
exit 0
