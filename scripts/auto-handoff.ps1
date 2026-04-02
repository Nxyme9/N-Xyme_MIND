<#
.SYNOPSIS
Detects terminal close and automatically triggers handoff capture for active sessions.

.DESCRIPTION
Monitors PowerShell process exit events and triggers handoff-capture.ps1 for active sessions.
Runs asynchronously to avoid blocking terminal close. Skips sessions with < 3 messages.

.PARAMETER SessionId
Optional: Specific session ID to monitor. If not provided, monitors all active sessions.

.PARAMETER MinMessages
Minimum number of messages required to trigger handoff (default: 3).

.EXAMPLE
.\auto-handoff.ps1
# Monitors all active sessions

.EXAMPLE
.\auto-handoff.ps1 -SessionId "ses_abc123"
# Monitors specific session

.EXAMPLE
.\auto-handoff.ps1 -MinMessages 5
# Only capture handoff for sessions with 5+ messages
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateNotNullOrEmpty()]
    [string]$SessionId,

    [Parameter(Mandatory=$false)]
    [ValidateRange(1, 100)]
    [int]$MinMessages = 3,

    [Parameter(Mandatory=$false)]
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: .\auto-handoff.ps1 [-SessionId <id>] [-MinMessages <count>]"
    Write-Host "  -SessionId    Specific session ID to monitor (optional)"
    Write-Host "  -MinMessages  Minimum messages to trigger handoff (default: 3)"
    exit
}

# Ensure we have the opencode CLI available
if (-not (Get-Command opencode -ErrorAction SilentlyContinue)) {
    Write-Host "Error: 'opencode' command not found. Please ensure OpenCode CLI is installed and in PATH." -ForegroundColor Red
    exit 1
}


Set-StrictMode -Version Latest

 

# Shared exit handling: one centralized On-ProcessExit function
function On-ProcessExit {
    param(
        [string]$SessionId,
        [int]$MinMessages,
        [string]$HandoffScript
    )

    Write-Host "`nTerminal close detected. Triggering auto-handoff..." -ForegroundColor Yellow
    
    $sessionsToCapture = @()
    if ($SessionId) {
        $messageCount = 0
        try {
            $exportJson = opencode export $SessionId 2>$null
            if ($exportJson) {
                $data = $exportJson | ConvertFrom-Json
                $messages = $data["messages"]
                if ($messages) { $messageCount = $messages.Count }
            }
        } catch { $messageCount = 0 }
        if ($messageCount -ge $MinMessages) {
            $sessionsToCapture += $SessionId
        } else {
            Write-Host "Skipping session $SessionId - only $messageCount messages (minimum: $MinMessages)" -ForegroundColor Gray
        }
    } else {
        try {
            $json = opencode session list --format json 2>$null
            if ($json) {
                $sessions = $json | ConvertFrom-Json
                foreach ($s in $sessions) {
                    $sid = $s.id
                    $exportJson = opencode export $sid 2>$null
                    $count = 0
                    if ($exportJson) {
                        $data = $exportJson | ConvertFrom-Json
                        $msgs = $data["messages"]
                        if ($msgs) { $count = $msgs.Count }
                    }
                    if ($count -ge $MinMessages) {
                        $sessionsToCapture += $sid
                    }
                }
            }
        } catch { }
    }
    
    $jobs = @()
    foreach ($sid in $sessionsToCapture) {
        $job = Start-Job -ScriptBlock {
            param($scriptPath, $sid2)
            try { & $scriptPath -SessionId $sid2 } catch { Write-Error "Handoff capture failed for session $sid2 : $_" }
        } -ArgumentList $HandoffScript, $sid
        $jobs += $job
    }
    if ($jobs.Count -gt 0) {
        Write-Host "Handoff capture initiated for $($jobs.Count) session(s)." -ForegroundColor Green
        Write-Host "Handoff files will be saved to .sisyphus/handoffs/" -ForegroundColor Green
    } else {
        Write-Host "No sessions met the minimum message threshold ($MinMessages)." -ForegroundColor Gray
    }
}

# Get script directory for handoff-capture.ps1
$scriptDir = $PSScriptRoot
$handoffCaptureScript = Join-Path -Path $scriptDir -ChildPath "handoff-capture.ps1"
if (-not (Test-Path $handoffCaptureScript)) {
    Write-Host "Error: handoff-capture.ps1 not found at $handoffCaptureScript" -ForegroundColor Red
    exit 1
}

# Register process exit event handler
$currentProcess = Get-Process -Id $PID
$processExitEvent = Register-ObjectEvent -InputObject $currentProcess -EventName "Exited" -Action {
    On-ProcessExit -SessionId $using:SessionId -MinMessages $using:MinMessages -HandoffScript $using:handoffCaptureScript
}

# Also register for PowerShell engine exit
$engineEvent = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    On-ProcessExit -SessionId $using:SessionId -MinMessages $using:MinMessages -HandoffScript $using:handoffCaptureScript
}

Write-Host "Auto-handoff monitor started." -ForegroundColor Green
Write-Host "Monitoring for terminal close events..." -ForegroundColor Green
if ($SessionId) {
    Write-Host "Target session: $SessionId" -ForegroundColor Cyan
} else {
    Write-Host "Monitoring all active sessions" -ForegroundColor Cyan
}
Write-Host "Minimum messages threshold: $MinMessages" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop monitoring." -ForegroundColor Yellow

# Keep the script running to monitor events
try {
    while ($true) {
        Start-Sleep -Seconds 1
        
        # Check if process is still running (in case of unexpected termination)
        if (-not (Get-Process -Id $PID -ErrorAction SilentlyContinue)) {
            break
        }
    }
} finally {
    # Clean up event handlers
    if ($processExitEvent) {
        Unregister-Event -SubscriptionId $processExitEvent.Id
    }
    if ($engineEvent) {
        Unregister-Event -SubscriptionId $engineEvent.Id
    }
    Write-Host "Auto-handoff monitor stopped." -ForegroundColor Yellow
}
