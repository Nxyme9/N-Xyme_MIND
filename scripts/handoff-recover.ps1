<#
.SYNOPSIS
    Lists available session handoff files and allows user to select one to resume.

.DESCRIPTION
    Scans the handoff directory for markdown files (excluding README.md and
    example.md), parses session metadata from each, and presents an interactive
    menu for selection. Outputs machine-readable session info for script
    consumption.

    ADHD-friendly: minimal cognitive load, simple numbered selection.

.PARAMETER HandoffDir
    Relative path to the handoff directory.
    Default: .sisyphus\handoffs

.PARAMETER ListOnly
    List available handoffs without prompting for selection.

.EXAMPLE
    .\handoff-recover.ps1
    Interactive handoff selection.

.EXAMPLE
    .\handoff-recover.ps1 -ListOnly
    List all available handoffs without selecting.

.OUTPUTS
    Machine-readable lines: SESSION_ID, SESSION_TITLE, SESSION_TIMESTAMP,
    SESSION_FILE, SESSION_SUMMARY
#>

[CmdletBinding()]
param(
    [ValidateNotNullOrEmpty()]
    [string]$HandoffDir = ".sisyphus\handoffs",
    [switch]$ListOnly
)

Set-StrictMode -Version Latest

# --- Resolve handoff directory path ---
$HandoffPath = Join-Path $PSScriptRoot ".." | Join-Path -ChildPath $HandoffDir
$resolved = Resolve-Path $HandoffPath -ErrorAction SilentlyContinue
if ($resolved) { $HandoffPath = $resolved.Path }
if (-not $HandoffPath) { $HandoffPath = Join-Path (Get-Location) $HandoffDir }

if (-not (Test-Path $HandoffPath)) {
    Write-Error "Handoff directory not found: $HandoffPath"
    exit 1
}

# --- Get all handoff files ---
$HandoffFiles = Get-ChildItem -Path $HandoffPath -Filter "*.md" |
    Where-Object { $_.Name -notmatch "^(README|example)\.md$" } |
    Sort-Object LastWriteTime -Descending

if ($HandoffFiles.Count -eq 0) {
    Write-Host "No handoff files found in $HandoffPath" -ForegroundColor Yellow
    exit 0
}

# --- Parse handoff files ---
$Handoffs = @()
foreach ($file in $HandoffFiles) {
    try {
        $content = Get-Content -Path $file.FullName -Raw -ErrorAction Stop
    } catch {
        Write-Warning "Failed to read '$($file.FullName)': $_"
        continue
    }

    # Extract session ID
    if ($content -match '\*\*Session ID\*\*:\s*(ses_[a-z0-9]+)') {
        $sessionId = $matches[1]
    } else {
        $sessionId = "unknown"
    }

    # Extract title
    if ($content -match '\*\*Title\*\*:\s*(.+)') {
        $title = $matches[1].Trim()
    } else {
        $title = "No title"
    }

    # Extract timestamp
    if ($content -match '\*\*Timestamp\*\*:\s*(\d{4}-\d{2}-\d{2}T\d{6}Z)') {
        $timestamp = $matches[1]
    } else {
        $timestamp = $file.LastWriteTime.ToString("yyyy-MM-ddTHHmmssZ")
    }

    # Extract summary
    if ($content -match '## Summary\s*\n(.+)') {
        $summary = $matches[1].Trim()
    } else {
        $summary = "No summary"
    }

    $Handoffs += [PSCustomObject]@{
        Index     = $Handoffs.Count + 1
        SessionId = $sessionId
        Title     = $title
        Timestamp = $timestamp
        Summary   = $summary
        File      = $file.FullName
        FileName  = $file.Name
    }
}

# --- Display available handoffs ---
Write-Host "`n=== Available Session Handoffs ===" -ForegroundColor Cyan
Write-Host "Found $($Handoffs.Count) handoff(s) in $HandoffPath`n" -ForegroundColor Gray

foreach ($h in $Handoffs) {
    Write-Host "[$($h.Index)] " -NoNewline -ForegroundColor Yellow
    Write-Host "$($h.SessionId)" -NoNewline -ForegroundColor Green
    Write-Host " - $($h.Title)" -ForegroundColor White
    Write-Host "    $($h.Timestamp)" -NoNewline -ForegroundColor Gray
    Write-Host " - $($h.Summary)" -ForegroundColor DarkGray
    Write-Host ""
}

# --- ListOnly mode: exit here ---
if ($ListOnly) {
    exit 0
}

# --- Prompt for selection ---
Write-Host "Select a handoff to resume (number or session ID): " -NoNewline -ForegroundColor Cyan
$selection = Read-Host

# --- Find selected handoff ---
$selected = $null
if ($selection -match '^\d+$') {
    $selected = $Handoffs | Where-Object { $_.Index -eq [int]$selection }
} else {
    $selected = $Handoffs | Where-Object { $_.SessionId -eq $selection }
}

if (-not $selected) {
    Write-Error "Invalid selection '$selection'"
    exit 1
}

# --- Output resume information ---
Write-Host "`n=== Resuming Session ===" -ForegroundColor Green
Write-Host "Resuming from handoff: $($selected.SessionId) - $($selected.Title)" -ForegroundColor Cyan
Write-Host "File: $($selected.FileName)" -ForegroundColor Gray
Write-Host ""

# --- Read and output the full handoff content ---
try {
    $handoffContent = Get-Content -Path $selected.File -Raw -ErrorAction Stop
} catch {
    Write-Error "Failed to read handoff file '$($selected.File)': $_"
    exit 1
}
Write-Host "=== Handoff Content ===" -ForegroundColor Yellow
Write-Host $handoffContent

# --- Machine-readable output for script consumption ---
Write-Host "`n=== Machine-Readable Output ===" -ForegroundColor Magenta
Write-Output "SESSION_ID=$($selected.SessionId)"
Write-Output "SESSION_TITLE=$($selected.Title)"
Write-Output "SESSION_TIMESTAMP=$($selected.Timestamp)"
Write-Output "SESSION_FILE=$($selected.File)"
Write-Output "SESSION_SUMMARY=$($selected.Summary)"
