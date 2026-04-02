<#
.SYNOPSIS
    Captures current session context and writes a Markdown handoff file.

.DESCRIPTION
    Reads session metadata, last messages, and todos from an OpenCode session
    via the CLI, then writes a structured Markdown handoff file to
    .sisyphus/handoffs/{SessionId}-{timestamp}.md following the handoff schema.

.PARAMETER SessionId
    Mandatory: session identifier (e.g., ses_abc123).

.EXAMPLE
    .\handoff-capture.ps1 -SessionId "ses_abc123"
    Captures a handoff file for session ses_abc123.

.OUTPUTS
    Markdown file at .sisyphus/handoffs/{SessionId}-{timestamp}.md.
#>

param(
  [Parameter(Mandatory=$true)]
  [ValidateNotNullOrEmpty()]
  [string]$SessionId
)

Set-StrictMode -Version Latest

# Small helper to truncate long content for readability
function Get-ContentTrunc {
  param(
    [Parameter(Mandatory=$true)][string]$Text,
    [int]$Max = 500
  )
  if ($null -eq $Text) { return "" }
  if ($Text.Length -le $Max) { return $Text }
  return $Text.Substring(0, $Max) + "..."
}

# Timestamp in UTC ISO 8601 (YYYY-MM-DDThhmmssZ)
$utcNow = [DateTime]::UtcNow
$timestampISO = $utcNow.ToString("yyyy-MM-dd'T'HHmmss'Z'")

# Output path (relative to repo root) as .sisyphus/handoffs/{sessionId}-{timestamp}.md
$handoffDir = Join-Path -Path (Get-Location) -ChildPath ".sisyphus/handoffs"
if (-not (Test-Path $handoffDir)) {
  New-Item -ItemType Directory -Path $handoffDir -Force | Out-Null
}
$handoffPath = Join-Path -Path $handoffDir -ChildPath ("{0}-{1}.md" -f $SessionId, $timestampISO)

# Retrieve session metadata
try {
  $infoRaw = & opencode session info --session-id $SessionId --json 2>$null
  if ($infoRaw -and $infoRaw -ne "") {
    $info = $infoRaw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if (-not $info) { $info = @{} }
  } else {
    $info = @{}
  }
} catch {
  $info = @{}
}

$title = if ($info.title) { $info.title } else { "(no title)" }
$workingDirectory = if ($info.working_directory) { $info.working_directory } else { (Get-Location).Path }
$agentsUsed = @()
if ($info.agents_used) { $agentsUsed = @($info.agents_used) }
$summary = if ($info.summary) { $info.summary } else { "" }

# Retrieve last messages and todos (limit to 10 as per schema)
$lastMessages = @()
$todos = @()
try {
  $readRaw = & opencode session read --session-id $SessionId --limit 10 --include-todos --json 2>$null
  if ($readRaw) {
    $readObj = $readRaw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if (-not $readObj) { $readObj = @{} }
    if ($readObj.last_messages) { $lastMessages = @($readObj.last_messages) }
    elseif ($readObj.messages) { $lastMessages = @($readObj.messages) }
    if ($readObj.todos) { $todos = @($readObj.todos) }
  }
} catch {
  $readObj = @{}
}

# Normalize messages to a common structure
$normalizedMessages = @()
foreach ($m in $lastMessages) {
  $role = ""
  $content = ""
  $ts = ""
  $agent = ""
  if ($m -is [hashtable] -or $m -is [psobject]) {
    if ($m.role) { $role = $m.role }
    if ($m.content) { $content = $m.content }
    if ($m.timestamp) { $ts = $m.timestamp }
    if ($m.agent) { $agent = $m.agent }
  } else {
    $content = [string]$m
  }
  if ($content -or $role) {
    $normalizedMessages += [pscustomobject]@{ role=$role; content=$content; timestamp=$ts; agent=$agent }
  }
}

# Build Markdown content following the Template in .sisyphus/handoffs/README.md
$lines = @()
$lines += "# Session Handoff"
$lines += ""
$lines += "## Session Info"
$lines += "- **Session ID**: $SessionId"
$lines += "- **Title**: $title"
$lines += ("- **Timestamp**: {0}" -f $timestampISO)
$lines += ("- **Working Directory**: {0}" -f $workingDirectory)
$lines += ""
$lines += "## Summary"
$lines += $summary
$lines += ""
$lines += "## Last Messages"
if ($normalizedMessages.Count -gt 0) {
  $idx = 1
  foreach ($msg in $normalizedMessages) {
    $ts = if ($msg.timestamp) { $msg.timestamp } else { "" }
    $role = if ($msg.role) { $msg.role } else { "" }
    $text = Get-ContentTrunc -Text ($msg.content) -Max 500
    $lines += ("{0}. [{1}] {2}: {3}" -f $idx, $ts, $role, $text)
    $idx++
  }
} else {
  $lines += "(no messages captured)"
}
$lines += ""
$lines += "## Todos"
if ($todos.Count -gt 0) {
  foreach ($td in $todos) {
    $id = if ($td.id) { $td.id } else { "" }
    $content = if ($td.content) { $td.content } else { "" }
    $status = if ($td.status) { $td.status } else { "" }
    $priority = if ($td.priority) { $td.priority } else { "" }
    $prefix = if ($id) { "[$id] " } else { "" }
    $todoLine = "- {0}{1} (Status: {2}{3})" -f $prefix, $content, $status, ( if ($priority) { ", Priority: $priority" } else { "" } )
    $lines += $todoLine
  }
} else {
  $lines += "(no todos)"
}
$lines += ""
$lines += "## Agents Used"
if ($agentsUsed.Count -gt 0) {
  foreach ($a in $agentsUsed) {
    $lines += "- $a"
  }
} else {
  $lines += "- (none)"
}

# Ensure parent directory exists for the handoff file
$parent = Split-Path -Path $handoffPath -Parent
if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }

# Write to file
$output = $lines -join "`n"
$output | Out-File -FilePath $handoffPath -Encoding utf8 -Force

Write-Output ("Handoff captured: {0}" -f $handoffPath)
