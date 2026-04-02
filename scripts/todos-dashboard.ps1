<#
.SYNOPSIS
    Displays global todos across all OpenCode sessions in ADHD-optimized views.

.DESCRIPTION
    Aggregates todos from all OpenCode sessions and presents them in three
    ADHD-friendly views: NOW (top 3 priority), TODAY (max 7), and WEEK (max 20).
    Each view is sorted by priority then status for minimal cognitive load.

.PARAMETER None
    This script takes no parameters. It automatically discovers all sessions
    with todos via the OpenCode CLI.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File ./scripts/todos-dashboard.ps1
    Displays the global todo dashboard with all three views.

.OUTPUTS
    Console output with formatted tables showing task, status, priority,
    session ID, and estimated time for each todo item.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest

# Status/Priority indicators
$STATUS_ICONS = @{
    "pending" = "[PENDING]"
    "in_progress" = "[ACTIVE]"
    "completed" = "[DONE]"
    "cancelled" = "[CANCEL]"
}

$PRIORITY_ICONS = @{
    "high" = "[HIGH]"
    "medium" = "[MED]"
    "low" = "[LOW]"
}

$TIME_ESTIMATES = @{
    "high" = "60 min"
    "medium" = "30 min"
    "low" = "15 min"
}

function Get-AllTodos {
    <#
    .SYNOPSIS
        Retrieves todos from all OpenCode sessions.
    .DESCRIPTION
        Lists all sessions, filters for those with todos, and aggregates
        todo items with session metadata.
    .OUTPUTS
        Array of PSCustomObject with Content, Status, Priority, SessionId, TimeEstimate.
    #>
    # Get all sessions
    try {
        $sessionsJson = & opencode session list --format json 2>$null
    } catch {
        Write-Error "Failed to list sessions: $_"
        return @()
    }
    if (-not $sessionsJson) { return @() }

    try {
        $sessions = $sessionsJson | ConvertFrom-Json
    } catch {
        Write-Error "Failed to parse session list JSON: $_"
        return @()
    }
    $allTodos = @()

    foreach ($s in $sessions) {
        if (-not $s.has_todos) { continue }

        # Get todos from session
        try {
            $todosJson = & opencode session read --session-id $s.id --include-todos --format json 2>$null
        } catch {
            Write-Warning "Failed to read session $($s.id): $_"
            continue
        }
        if (-not $todosJson) { continue }

        try {
            $sessionData = $todosJson | ConvertFrom-Json
        } catch {
            Write-Warning "Failed to parse session data for $($s.id): $_"
            continue
        }
        if ($sessionData.todos) {
            foreach ($t in $sessionData.todos) {
                $allTodos += [PSCustomObject]@{
                    Content = $t.content
                    Status = $t.status
                    Priority = if ($t.priority) { $t.priority } else { "medium" }
                    SessionId = if ($s.id) { $s.id.Substring(0, [Math]::Min(12, $s.id.Length)) } else { "unknown..." }
                    TimeEstimate = if ($TIME_ESTIMATES.ContainsKey($t.priority)) { $TIME_ESTIMATES[$t.priority] } else { "30 min" }
                }
            }
        }
    }

    return $allTodos
}

function Sort-Todos {
    <#
    .SYNOPSIS
        Sorts todos by priority then status.
    .PARAMETER todos
        Array of todo objects to sort.
    .OUTPUTS
        Sorted array of todo objects.
    #>
    param($todos)
    $priorityOrder = @{ "high" = 0; "medium" = 1; "low" = 2 }
    $statusOrder = @{ "in_progress" = 0; "pending" = 1; "completed" = 2; "cancelled" = 3 }

    return $todos | Sort-Object {
        $priorityOrder[$_.Priority]
    }, {
        $statusOrder[$_.Status]
    }
}

function Display-View {
    <#
    .SYNOPSIS
        Displays a filtered view of todos as a formatted table.
    .PARAMETER title
        Title for the view section.
    .PARAMETER todos
        Array of todo objects to display.
    .PARAMETER maxCount
        Maximum number of todos to show in this view.
    #>
    param([string]$title, $todos, [int]$maxCount)

    $limited = $todos | Select-Object -First $maxCount
    if ($limited.Count -eq 0) {
        Write-Host "`n${title}: No tasks" -ForegroundColor Gray
        return
    }

    Write-Host "`n${title} ($($limited.Count) tasks)" -ForegroundColor Cyan
    Write-Host "-" * 80 -ForegroundColor DarkGray

    $table = $limited | ForEach-Object {
        [PSCustomObject]@{
            "Task" = $_.Content.Substring(0, [Math]::Min(50, $_.Content.Length)) + $(if($_.Content.Length -gt 50){"..."}else{""})
            "Status" = "$($STATUS_ICONS[$_.Status]) $($_.Status)"
            "Priority" = "$($PRIORITY_ICONS[$_.Priority]) $($_.Priority)"
            "Session" = $_.SessionId
            "Time" = $_.TimeEstimate
        }
    }

    $table | Format-Table -AutoSize
}

# Main
Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "  GLOBAL TODO DASHBOARD - ADHD-Optimized Views" -ForegroundColor Cyan

$allTodos = Get-AllTodos
if ($allTodos.Count -eq 0) {
    Write-Host "`nNo todos found across any sessions." -ForegroundColor Yellow
    exit 0
}

$sorted = Sort-Todos -todos $allTodos

# Build views
$nowTodos = $sorted | Where-Object { $_.Status -in @("in_progress", "pending") }
$todayTodos = $sorted | Where-Object { $_.Status -notin @("completed", "cancelled") }
$weekTodos = $sorted

Display-View -title "NOW (Top 3 Priority)" -todos $nowTodos -maxCount 3
Display-View -title "TODAY (Max 7)" -todos $todayTodos -maxCount 7
Display-View -title "WEEK (Max 20)" -todos $weekTodos -maxCount 20

Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "  Total: $($allTodos.Count) todos across sessions" -ForegroundColor Gray
Write-Host "===========================================================`n" -ForegroundColor Cyan
