<#
.SYNOPSIS
    Produces AKASHA-formatted archive entries from an OpenCode session.

.DESCRIPTION
    Reads session content via the OpenCode CLI, extracts messages matching
    AKASHA filter criteria (architectural decisions, code snippets, research,
    error solutions), and writes a Markdown archive file to .akasha/sessions/.

    Sessions with fewer than 5 messages are skipped automatically.

.PARAMETER SessionId
    The session ID to filter and archive (e.g., "ses_xxx").

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File ./scripts/akasha-filter.ps1 -SessionId "ses_abc123"
    Filters and archives the specified session.

.OUTPUTS
    Creates a Markdown file in .akasha/sessions/ named {SessionId}-{timestamp}.md.
#>

Set-StrictMode -Version Latest

param(
  [Parameter(Mandatory = $true, Position = 0)]
  [ValidateNotNullOrEmpty()]
  [string]$SessionId
)

function Get-SessionContent {
  param([string]$sid)
  # Try the built-in session_read tool
  try {
    if (Get-Command -Name opencode -ErrorAction SilentlyContinue) {
      # Use the OpenCode CLI with explicit JSON output flags
      $raw = & opencode session read --session-id $sid --format json
      return $raw
    }
  } catch {
    # fall through to fallback
  }
  # Fallback: try local session blob if present
  $scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
  $fallbackPath = Join-Path -Path (Split-Path -Parent $scriptRoot) -ChildPath ".sessions"
  $blob = Join-Path -Path $fallbackPath -ChildPath ( $sid + ".json" )
  if (Test-Path $blob) {
    try {
      $text = Get-Content -Path $blob -Raw
      return $text
    } catch {
      return $null
    }
  }
  return $null
}

function Parse-SessionInfo {
  param([string]$sid)
  if (Get-Command -Name opencode -ErrorAction SilentlyContinue) {
    try {
      $raw = & opencode session info --session-id $sid --format json
      if ($raw) {
        if ($raw -is [string]) {
          try { return $raw | ConvertFrom-Json } catch { return $raw }
        } else { return $raw }
      }
    } catch {
      return $null
    }
  }
  return $null
}

function Extract-AKASHAEntries {
  param(
    [string]$Text,
    [hashtable]$SessionMeta
  )

  if ([string]::IsNullOrEmpty($Text)) { return @() }
  
  $entries = @()
  $blocks = @()
  
  # Try to parse as JSON session file first
  $jsonParsed = $null
  try {
    $jsonParsed = $Text | ConvertFrom-Json -ErrorAction SilentlyContinue
  } catch {
    # Not valid JSON, treat as plain text
  }
  
  if ($jsonParsed -and $jsonParsed.messages) {
    # JSON session format - extract individual messages
    foreach ($msg in $jsonParsed.messages) {
      if ($msg.content) {
        $blocks += $msg.content
      }
    }
  } else {
    # Plain text format - split by blank lines
    $blocks = ($Text -split "(?m)(\r?\n){2,}")
  }
  
  foreach ($block in $blocks) {
    if ($block -match "Architectural decision|Decision:|Architecture|Error|exception|stack|http|https|priority|completed|Code snippet|snippet") {
      $title = (($block -split "`n")[0]).Trim()
      if ([string]::IsNullOrWhiteSpace($title)) { $title = "AKASHA Entry" }
      $src = if ($SessionMeta -and $SessionMeta.SessionId) { $SessionMeta.SessionId } else { $SessionMeta }
      $date = if ($SessionMeta -and $SessionMeta.Date) { $SessionMeta.Date } elseif ($SessionMeta -and $SessionMeta.date) { $SessionMeta.date } else { (Get-Date).ToString("yyyy-MM-dd") }
      $tags = @()
      if ($block -match "Architectural decision|Architecture") { $tags += "architecture"; $tags += "design" }
      if ($block -match "Error|exception|stack") { $tags += "error"; $tags += "debug" }
      if ($block -match "http|https") { $tags += "external" }
      if ($block -match "Code snippet|snippet|file|pattern") { $tags += "code" }
      if ($tags.Count -eq 0) { $tags += "knowledge" }
      $summary = ($block -replace "[\r\n]+", " ").Trim()
      if ($summary.Length -gt 260) { $summary = $summary.Substring(0,260) + "..." }
      $entry = [ordered]@{
        Title = $title
        Source = if ($src) { $src } else { "session:$src" }
        Date = $date
        Importance = 5
        Tags = ($tags | Select-Object -Unique)
        Summary = $summary
        Content = $block.Trim()
      }
      $entries += [pscustomobject]$entry
    }
  }
  return $entries
}

function Write-AKASHAOutput {
  param(
    [array]$Entries,
    [string]$SessionId,
    [string]$RootPath
  )

  $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $outDir = Join-Path -Path $RootPath -ChildPath ".akasha/sessions"
  if (-Not (Test-Path $outDir)) { New-Item -Path $outDir -ItemType Directory -Force | Out-Null }
  $outPath = Join-Path -Path $outDir -ChildPath ( "$SessionId-$timestamp.md" )
  
  $content = ""
  if ($Entries.Count -eq 0) {
    $content = "# AKASHA Archive`nNo eligible AKASHA entries found in this session."
  } else {
    $lines = @()
    foreach ($e in $Entries) {
      $lines += "- Title: $($e.Title)"
      $lines += "  Source: $($e.Source)"
      $lines += "  Date: $($e.Date)"
      $lines += "  Importance: $($e.Importance)"
      $lines += "  Tags: " + (($e.Tags -join ", "))
      $lines += "  Summary: $($e.Summary)"
      $lines += "  Content:|"
      foreach ($line in $e.Content -split "`n") {
        $lines += "    $line"
      }
      $lines += ""
    }
    $content = $lines -join "`n"
  }
  
  # Write without BOM
  [System.IO.File]::WriteAllText($outPath, $content, [System.Text.UTF8Encoding]::new($false))
  return $outPath
}

try {
  # Resolve session metadata
  $sessionMeta = Parse-SessionInfo -sid $SessionId
  if (-not $sessionMeta) {
    # fallback to minimal metadata
    $sessionMeta = @{ SessionId = $SessionId; Date = (Get-Date).ToString("yyyy-MM-dd") }
  } else {
    if ($sessionMeta -isnot [hashtable]) { $sessionMeta = @{ SessionId = $SessionId; Date = (Get-Date).ToString("yyyy-MM-dd") } }
  }

  # Retrieve content and check message count if possible
  $content = Get-SessionContent -sid $SessionId
  if ([string]::IsNullOrWhiteSpace($content)) {
    Write-Host "No session content found for SessionId=$SessionId" -ForegroundColor Yellow
    exit 0
  }

  # If we can derive a message count from the content, enforce min 5 messages
  $msgCount = 0
  # Try to parse JSON to get accurate message count
  $jsonParsed = $null
  try {
    $jsonParsed = $content | ConvertFrom-Json -ErrorAction SilentlyContinue
  } catch {}
  
  if ($jsonParsed -and $jsonParsed.messages) {
    $msgCount = $jsonParsed.messages.Count
  } elseif ($jsonParsed -and $jsonParsed.metadata -and $jsonParsed.metadata.messageCount) {
    $msgCount = $jsonParsed.metadata.messageCount
  } else {
    # Fallback: count newlines as proxy for message count
    $msgCount = ([regex]::Matches($content, "\n").Count) + 1
  }
  
  if ($msgCount -lt 5) {
    Write-Host "Session contains fewer than 5 messages ($msgCount). Skipping AKASHA archival." -ForegroundColor Yellow
    exit 0
  }

  # Load AKASHA schema for guidance (if available)
  $scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
  $akashaSchemaPath = Join-Path -Path (Split-Path -Parent $scriptRoot) -ChildPath ".akasha/README.md"
  $schemaInfo = @()
  if (Test-Path $akashaSchemaPath) {
    $schemaInfo = Get-Content -Path $akashaSchemaPath -Raw
  }

  # Build AKASHA entries from the session content
  $entries = Extract-AKASHAEntries -Text $content -SessionMeta $sessionMeta
  # Write output to disk
  $rootPath = (Split-Path -Parent $scriptRoot)
  $outPath = Write-AKASHAOutput -Entries $entries -SessionId $SessionId -RootPath $rootPath

  # Persist a lightweight log/trace in the local notepad (append learnings)
  $notepadRoot = Join-Path -Path $rootPath -ChildPath ".sisyphus/notepads/session-management-system/learnings.md"
  if (-not (Test-Path $notepadRoot)) {
    $dir = Split-Path -Path $notepadRoot -Parent
    if (-not (Test-Path $dir)) { New-Item -Path $dir -ItemType Directory -Force | Out-Null }
    New-Item -Path $notepadRoot -ItemType File -Force | Out-Null
  }
  $entryCount = @($entries).Count
  $noteLine = "- AKASHA filter run on SessionId=$SessionId at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -> entries=$entryCount"
  Add-Content -Path $notepadRoot -Value $noteLine

  if (Test-Path $outPath) {
    Write-Host "AKASHA archive created: $outPath" -ForegroundColor Green
  } else {
    Write-Host "AKASHA archive could not be created." -ForegroundColor Red
  }
} catch {
  Write-Error "Failed to generate AKASHA filter: $_"
  exit 1
}
