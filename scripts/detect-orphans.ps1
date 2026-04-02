<#
.SYNOPSIS
    Detects orphaned OpenCode sessions and prints a sortable table.

.DESCRIPTION
    Scans all OpenCode sessions via the CLI, classifies each as Active, Stale,
    or Orphaned based on message count and agent presence. Sessions spawned by
    sub-agents matching the configured spawn-pattern are flagged as orphans.

    Thresholds and the spawn-agent pattern can be overridden via parameters or
    a JSON config file at .sisyphus/session-config.json.

.PARAMETER SpawnPattern
    Regex pattern used to identify sub-agent spawn sessions.
    Default: loaded from config or "(?i)(Sisyphus|Prometheus)".

.PARAMETER OrphanThreshold
    Message count below which a session with no agents is considered orphaned.
    Default: 5

.PARAMETER ActiveThreshold
    Message count above which a session is classified as Active.
    Default: 10

.PARAMETER ConfigPath
    Path to JSON config file containing SpawnPattern, OrphanThreshold, ActiveThreshold.
    Defaults are used if file is missing.

.EXAMPLE
    .\detect-orphans.ps1
    Detect orphans using default thresholds.

.EXAMPLE
    .\detect-orphans.ps1 -SpawnPattern "(?i)Oracle" -OrphanThreshold 3
    Detect orphans with custom spawn pattern and threshold.

.OUTPUTS
    PSCustomObject table with columns: SessionID, Messages, Agents, Status, Reason
#>

[CmdletBinding()]
param(
    [string]$SpawnPattern,
    [int]$OrphanThreshold,
    [int]$ActiveThreshold,
    [string]$ConfigPath
)

Set-StrictMode -Version Latest

# --- Constants / Defaults ---
$script:DEFAULT_SPAWN_PATTERN   = "(?i)(Sisyphus|Prometheus)"
$script:DEFAULT_ORPHAN_THRESHOLD = 5
$script:DEFAULT_ACTIVE_THRESHOLD = 10

# --- Config loading ---
function Import-SessionConfig {
    param([string]$Path)
    $config = @{
        SpawnPattern    = $script:DEFAULT_SPAWN_PATTERN
        OrphanThreshold = $script:DEFAULT_ORPHAN_THRESHOLD
        ActiveThreshold = $script:DEFAULT_ACTIVE_THRESHOLD
    }
    if ($Path -and (Test-Path $Path)) {
        try {
            $json = Get-Content -Path $Path -Raw | ConvertFrom-Json
            if ($json.SpawnPattern)    { $config.SpawnPattern    = $json.SpawnPattern }
            if ($json.OrphanThreshold) { $config.OrphanThreshold = [int]$json.OrphanThreshold }
            if ($json.ActiveThreshold) { $config.ActiveThreshold = [int]$json.ActiveThreshold }
        } catch {
            Write-Warning "Failed to parse config '$Path': $_. Using defaults."
        }
    }
    return $config
}

# Resolve config path
$resolvedConfigPath = if ($ConfigPath) { $ConfigPath } else {
    Join-Path $PSScriptRoot "..\.sisyphus\session-config.json"
}
$config = Import-SessionConfig -Path $resolvedConfigPath

# Parameters override config; config overrides defaults
$SpawnPattern    = if ($PSBoundParameters.ContainsKey('SpawnPattern'))    { $SpawnPattern }    else { $config.SpawnPattern }
$OrphanThreshold = if ($PSBoundParameters.ContainsKey('OrphanThreshold')) { $OrphanThreshold } else { $config.OrphanThreshold }
$ActiveThreshold = if ($PSBoundParameters.ContainsKey('ActiveThreshold')) { $ActiveThreshold } else { $config.ActiveThreshold }

# Ensure we have the opencode CLI available
if (-not (Get-Command opencode -ErrorAction SilentlyContinue)) {
    Write-Error "opencode command not found. Please ensure OpenCode CLI is installed and in PATH."
    exit 1
}

# --- Functions ---

function Get-SessionList {
    <#
    .SYNOPSIS Retrieves the list of all OpenCode sessions as JSON.
    #>
    try {
        $json = opencode session list --format json 2>$null
    } catch {
        Write-Error "Failed to execute 'opencode session list': $_"
        return @()
    }
    if (-not $json) {
        Write-Warning "No sessions found."
        return @()
    }
    try {
        $sessions = $json | ConvertFrom-Json
        return ,$sessions
    } catch {
        Write-Error "Failed to parse session list JSON: $_"
        return @()
    }
}

function Get-SessionDetails {
    param([string]$SessionID)
    try {
        $exportJson = opencode export $SessionID --format json 2>$null
    } catch {
        Write-Warning "Failed to execute 'opencode export' for session $SessionID : $_"
        return $null
    }
    if (-not $exportJson) {
        return $null
    }
    try {
        $data = $exportJson | ConvertFrom-Json
        $messages = $data["messages"]
        $messageCount = if ($messages) { $messages.Count } else { 0 }
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
        Write-Warning "Failed to parse export for session $SessionID : $_"
        return $null
    }
}

function Format-Agents {
    param([array]$AgentsArray)
    if (-not $AgentsArray -or $AgentsArray.Count -eq 0) { return "" }
    return ($AgentsArray | ForEach-Object { $_.ToString() } | Where-Object { $_ -ne '' }) -join ", "
}

# --- Main ---
Write-Host "Detecting orphaned OpenCode sessions..." -ForegroundColor Cyan
Write-Host "  Spawn pattern: $SpawnPattern | Orphan threshold: $OrphanThreshold | Active threshold: $ActiveThreshold" -ForegroundColor DarkGray

$sessions = Get-SessionList
if ($sessions.Count -eq 0) {
    Write-Host "No sessions found." -ForegroundColor Gray
    exit 0
}

Write-Host "Found $($sessions.Count) sessions. Analyzing each..." -ForegroundColor Cyan

$rows = @()
$processed = 0
foreach ($s in $sessions) {
    $processed++
    Write-Progress -Activity "Analyzing sessions" -Status "$processed of $($sessions.Count)" -PercentComplete (($processed / $sessions.Count) * 100)

    $id = $s["id"]
    $title = $s["title"]

    $details = Get-SessionDetails -SessionID $id
    if (-not $details) {
        $rows += [pscustomobject]@{
            SessionID = $id
            Title     = $title
            Messages  = 0
            Agents    = ""
            Status    = "Orphaned (export failed)"
            Reason    = "Failed to export session data"
        }
        continue
    }

    $messages = $details.MessageCount
    $agents = Format-Agents -AgentsArray $details.Agents

    # Spawn check: sub-agent with < 5 messages matching spawn pattern
    $spawnFlag = $false
    if ($agents -and $agents -match "(?i)(Sisyphus|Prometheus)" -and $messages -lt 5) { $spawnFlag = $true }

    # Orphan condition: (<5 msgs AND no agents) OR spawn flag
    $orphan = ( (($messages -lt 5) -and ([string]::IsNullOrWhiteSpace($agents)) ) -or $spawnFlag )

    # Status determination
    if ($orphan) {
        $status = "Orphaned"
    } elseif ($messages -gt $ActiveThreshold) {
        $status = "Active"
    } else {
        $status = "Stale"
    }

    # Reason field
    $reasons = @()
    if ($spawnFlag) { $reasons += "Spawned by sub-agent matching '$SpawnPattern'" }
    if (($messages -lt $OrphanThreshold) -and ([string]::IsNullOrWhiteSpace($agents))) {
        $reasons += "< $OrphanThreshold messages and no agents"
    }
    $reason = if ($reasons.Count -gt 0) { ($reasons -join "; ") } else { "" }

    $rows += [pscustomobject]@{
        SessionID = $id
        Title     = $title
        Messages  = $messages
        Agents    = $agents
        Status    = $status
        Reason    = $reason
    }
}

Write-Progress -Activity "Analyzing sessions" -Completed

if ($rows.Count -eq 0) {
    Write-Host "No orphan candidates found." -ForegroundColor Gray
    exit 0
}

# Sort: orphaned first, then by message count descending
$sorted = $rows | Sort-Object -Property @{Expression = { if ($_.Status -eq 'Orphaned') { 0 } else { 1 } } }, @{Expression = { - $_.Messages } }

# Output as a clean table
$sorted | Select-Object SessionID, Messages, Agents, Status, Reason | Format-Table -AutoSize

# Summary
$orphanCount = ($sorted | Where-Object { $_.Status -eq 'Orphaned' }).Count
$activeCount = ($sorted | Where-Object { $_.Status -eq 'Active' }).Count
$staleCount  = ($sorted | Where-Object { $_.Status -eq 'Stale' }).Count

Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Total sessions: $($rows.Count)" -ForegroundColor White
Write-Host "  Orphaned: $orphanCount" -ForegroundColor Red
Write-Host "  Active: $activeCount" -ForegroundColor Green
Write-Host "  Stale: $staleCount" -ForegroundColor Yellow

exit 0
