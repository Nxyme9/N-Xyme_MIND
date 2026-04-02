<#
.SYNOPSIS
    Renames OpenCode sessions in the SQLite database to Agent-N titles.

.DESCRIPTION
    Updates the title column in the SessionMetadata table of opencode.db for a
    predefined list of sessions. The current session is always skipped to avoid
    self-modification. Session mappings can be provided via a JSON config file
    or the default hardcoded list.

    Requires sqlite3.exe in PATH.

.PARAMETER ConfigPath
    Path to a JSON file containing an array of session rename mappings.
    Each entry: { "ses": "ses_...", "title": "Agent-N - ..." }
    If omitted, uses the built-in default mappings.

.PARAMETER DbPath
    Path to the opencode.db SQLite database.
    Default: $Env:USERPROFILE\.config\opencode\opencode.db

.PARAMETER CurrentSession
    Session ID to skip (the running session).
    No default; pass explicitly to avoid renaming the active session.

.EXAMPLE
    .\rename-sessions.ps1
    Rename sessions using default mappings.

.EXAMPLE
    .\rename-sessions.ps1 -ConfigPath .\.sisyphus\session-renames.json
    Rename sessions using a custom config file.

.OUTPUTS
    None. Writes status messages to the console.
#>

[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium')]
param(
    [string]$ConfigPath,
    [string]$DbPath,
    [string]$CurrentSession
)

Set-StrictMode -Version Latest

# --- Resolve database path ---
if (-not $DbPath) {
    $DbPath = Join-Path $Env:USERPROFILE ".config\opencode\opencode.db"
}
if (-not (Test-Path $DbPath)) {
    Write-Error "Database not found at $DbPath"
    exit 2
}

# --- Default session mappings (load from config or use empty array) ---
$configPath = Join-Path $PSScriptRoot ".." "configs" "session-rename-map.json"
if (Test-Path $configPath) {
    $defaultUpdates = Get-Content $configPath | ConvertFrom-Json
} else {
    $defaultUpdates = @()
}

# --- Load mappings from config or defaults ---
if ($ConfigPath -and (Test-Path $ConfigPath)) {
    try {
        $updates = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
        Write-Host "Loaded $($updates.Count) mappings from $ConfigPath" -ForegroundColor DarkGray
    } catch {
        Write-Warning "Failed to parse config '$ConfigPath': $_. Using defaults."
        $updates = $defaultUpdates
    }
} else {
    $updates = $defaultUpdates
}

# --- Validate sqlite3 is available ---
if (-not (Get-Command sqlite3 -ErrorAction SilentlyContinue)) {
    Write-Error "sqlite3.exe not found in PATH. Please install SQLite CLI."
    exit 3
}

# --- Rename function ---
function Update-SessionTitle {
  param([string]$SessionId, [string]$NewTitle)
  # Only allow known columns to be used in the WHERE clause to prevent injection.
  $columns = @("session_id", "session", "id")
  foreach ($col in $columns) {
    # Parameterize the value in the WHERE clause to prevent SQL injection.
    $qry = "SELECT 1 FROM SessionMetadata WHERE $col = ? LIMIT 1;"
    $exists = (& sqlite3 "$DbPath" $qry $SessionId) 2>$null
    if ($exists -and $exists.Trim() -eq "1") {
      $updateQry = "UPDATE SessionMetadata SET title = ? WHERE $col = ?;"
      & sqlite3 "$DbPath" $updateQry $NewTitle $SessionId
      if ($LASTEXITCODE -eq 0) { return $true }
    }
  }
  return $false
}

# --- Main ---
$updatedCount = 0
foreach ($item in $updates) {
    $sessionId = $item.ses
    $newTitle  = $item.title

    if ($sessionId -eq $CurrentSession) {
        Write-Host "Skipping current session $sessionId" -ForegroundColor Yellow
        continue
    }

    if ($PSCmdlet.ShouldProcess($sessionId, "Rename to '$newTitle'")) {
        if (Update-SessionTitle -SessionId $sessionId -NewTitle $newTitle) {
            $updatedCount++
            Write-Host "Updated $sessionId -> '$newTitle'" -ForegroundColor Green
        } else {
            Write-Warning "No matching row found for session $sessionId."
        }
    }
}

if ($updatedCount -eq $updates.Count) {
    Write-Host "Renamed all $($updates.Count) sessions successfully" -ForegroundColor Green
} else {
    Write-Host "Renamed $updatedCount of $($updates.Count) sessions; some may be missing or already renamed." -ForegroundColor Yellow
}

exit 0
