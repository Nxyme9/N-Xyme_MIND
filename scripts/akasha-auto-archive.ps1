<#
.SYNOPSIS
    Auto-archives OpenCode sessions to the AKASHA permanent archive.

.DESCRIPTION
    Filters session content for essential knowledge (architectural decisions,
    code snippets, research findings, error solutions) and saves filtered
    entries to .akasha/sessions/ as Markdown files. Updates the archive index
    automatically.

.PARAMETER SessionId
    The specific session ID to archive (e.g., "ses_xxx").

.PARAMETER All
    Archive all sessions with 5+ messages.

.PARAMETER DryRun
    Preview what would be archived without writing files.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File ./scripts/akasha-auto-archive.ps1 -SessionId "ses_abc123"
    Archives a specific session.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File ./scripts/akasha-auto-archive.ps1 -All
    Archives all sessions with sufficient messages.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File ./scripts/akasha-auto-archive.ps1 -All -DryRun
    Previews which sessions would be archived.

.OUTPUTS
    Creates Markdown files in .akasha/sessions/ and updates .akasha/index.md.
#>

[CmdletBinding()]
param(
    [ValidateNotNullOrEmpty()]
    [string]$SessionId,

    [switch]$All,
    [switch]$DryRun
)

Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$akashaDir = Join-Path $repoRoot ".akasha\sessions"
$indexFile = Join-Path $repoRoot ".akasha\index.md"

# Ensure AKASHA directories exist
$dirs = @("sessions", "decisions", "code-snippets", "research", "todos")
foreach ($d in $dirs) {
    $path = Join-Path $repoRoot ".akasha\$d"
    if (-not (Test-Path $path)) { New-Item -ItemType Directory -Path $path -Force | Out-Null }
}

# Filter criteria for AKASHA
$filterKeywords = @(
    "architectural decision", "architecture", "design decision",
    "code snippet", "pattern", "implementation",
    "research", "finding", "conclusion",
    "error solution", "fix", "workaround",
    "completed", "important", "critical"
)

function Filter-SessionContent {
    <#
    .SYNOPSIS
        Filters session messages for AKASHA-worthy content.
    .PARAMETER sessionData
        Parsed session data object with messages array.
    .OUTPUTS
        Array of message objects matching filter keywords.
    #>
    param($sessionData)

    $filtered = @()
    foreach ($msg in $sessionData.messages) {
        if ($null -ne $msg.content) {
            $content = $msg.content.ToLower()
        } else {
            $content = ""
        }
        foreach ($keyword in $filterKeywords) {
            if ($content -match $keyword) {
                $filtered += $msg
                break
            }
        }
    }
    return $filtered
}

function Archive-Session {
    <#
    .SYNOPSIS
        Archives a single session to the AKASHA directory.
    .PARAMETER sessionId
        The session ID to archive.
    .OUTPUTS
        Boolean indicating success.
    #>
    param([string]$sessionId)

    # Read session
    try {
        $sessionJson = & opencode session read --session-id $sessionId --format json 2>$null
    } catch {
        Write-Host "ERROR: Could not read session $sessionId - $_" -ForegroundColor Red
        return $false
    }
    if (-not $sessionJson) {
        Write-Host "ERROR: Could not read session $sessionId" -ForegroundColor Red
        return $false
    }

    try {
        $session = $sessionJson | ConvertFrom-Json
    } catch {
        Write-Host "ERROR: Failed to parse session JSON for $sessionId - $_" -ForegroundColor Red
        return $false
    }

    # Filter content
    $filtered = Filter-SessionContent -sessionData $session
    if ($filtered.Count -eq 0) {
        Write-Host "SKIP: No essential content found in $sessionId" -ForegroundColor Yellow
        return $false
    }

    # Generate archive entry
    $timestamp = Get-Date -Format "yyyy-MM-ddTHHmmssZ"
    $filename = "$sessionId-$timestamp.md"
    $filepath = Join-Path $akashaDir $filename

    if ($DryRun) {
        Write-Host "[DRY RUN] Would archive: $filename ($($filtered.Count) filtered messages)" -ForegroundColor Yellow
        return $true
    }

    # Build archive content
    $content = @"
# Session Archive: $sessionId

## Metadata
- **Source**: session://$sessionId
- **Date**: $timestamp
- **Importance**: 3
- **Tags**: [session, auto-archived]
- **Summary**: Auto-archived session with $($filtered.Count) essential messages

## Content

"@

    foreach ($msg in $filtered) {
        $role = if ($msg.role -eq "user") { "[User]" } else { "[Assistant]" }
        $content += "### $role ($($msg.timestamp))`n`n$($msg.content)`n`n---`n`n"
    }

    # Write archive file
    $content | Out-File -FilePath $filepath -Encoding UTF8
    Write-Host "ARCHIVED: $filename ($($filtered.Count) messages)" -ForegroundColor Green

    # Update index
    Update-Index -filename $filename -sessionId $sessionId -date $timestamp -summary "Auto-archived session"

    return $true
}

function Update-Index {
    <#
    .SYNOPSIS
        Updates the AKASHA index file with a new archive entry.
    .PARAMETER filename
        The archive filename.
    .PARAMETER sessionId
        The session ID.
    .PARAMETER date
        The archive date.
    .PARAMETER summary
        Brief summary of the archive.
    #>
    param($filename, $sessionId, $date, $summary)

    $entry = "| [$date]($filename) | $sessionId | 3 | session, auto-archived | $summary |`n"

    if (Test-Path $indexFile) {
        Add-Content -Path $indexFile -Value $entry
    } else {
        $header = @"
# AKASHA Knowledge Archive Index

| Date | Source | Importance | Tags | Summary |
|------|--------|------------|------|---------|
"@
        Set-Content -Path $indexFile -Value ($header + "`n" + $entry)
    }
}

# Main
Write-Host "`n═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  [ARCHIVE] AKASHA AUTO-ARCHIVER" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan

if ($SessionId) {
    Write-Host "`nArchiving session: $SessionId" -ForegroundColor Gray
    Archive-Session -sessionId $SessionId
} elseif ($All) {
    Write-Host "`nArchiving all sessions..." -ForegroundColor Gray
    try {
        $sessionsJson = & opencode session list --format json 2>$null
    } catch {
        Write-Host "ERROR: Failed to list sessions - $_" -ForegroundColor Red
        exit 1
    }
    if ($sessionsJson) {
        try {
            $sessions = $sessionsJson | ConvertFrom-Json
        } catch {
            Write-Host "ERROR: Failed to parse session list JSON - $_" -ForegroundColor Red
            exit 1
        }
        $archivedCount = 0
        foreach ($s in $sessions) {
            if ($s.message_count -lt 5) { continue }  # Skip orphans
            if (Archive-Session -sessionId $s.id) { $archivedCount++ }
        }
        Write-Host "`nArchived $archivedCount of $($sessions.Count) sessions" -ForegroundColor Cyan
    }
} else {
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  -SessionId 'ses_xxx'  Archive specific session"
    Write-Host "  -All                  Archive all sessions"
    Write-Host "  -DryRun               Preview without writing"
}

Write-Host "`n═══════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan
