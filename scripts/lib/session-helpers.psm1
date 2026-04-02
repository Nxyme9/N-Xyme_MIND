#Requires -Version 5.1
Set-StrictMode -Version Latest

<#
.SYNOPSIS
    Shared PowerShell module for OpenCode session management.
.DESCRIPTION
    Provides helper functions for querying, formatting, and classifying
    OpenCode sessions based on configurable thresholds.
.NOTES
    Module: session-helpers
    Version: 1.0.0
#>

# ── Load Configuration ───────────────────────────────────────────────────────
$Script:ConfigPath = Join-Path $PSScriptRoot 'session-config.psd1'
if (Test-Path $Script:ConfigPath) {
    $Script:Config = Import-PowerShellDataFile -Path $Script:ConfigPath
} else {
    throw "Configuration file not found: $Script:ConfigPath"
}

# ── Helper Functions ─────────────────────────────────────────────────────────

function Format-Agents {
    <#
    .SYNOPSIS
        Formats an array of agent names into a comma-separated string.
    .PARAMETER Agents
        Array of agent name strings.
    .OUTPUTS
        System.String — Comma-separated agent list, or "(none)" if empty.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory, ValueFromPipeline)]
        [AllowEmptyCollection()]
        [string[]]$Agents
    )

    process {
        try {
            if ($null -eq $Agents -or $Agents.Count -eq 0) {
                return '(none)'
            }
            return ($Agents -join ', ')
        }
        catch {
            Write-Error "$($Script:Config.ErrorPrefix): Failed to format agents — $_"
            return '(error)'
        }
    }
}

function Get-SessionList {
    <#
    .SYNOPSIS
        Retrieves the list of all OpenCode sessions.
    .DESCRIPTION
        Calls `opencode session list --format json` and returns an array of
        session objects with Id, Messages, First, Last, and Agents properties.
    .OUTPUTS
        System.Object[] — Array of session objects. Returns empty array on failure.
    #>
    [CmdletBinding()]
    [OutputType([object[]])]
    param()

    process {
        try {
            $jsonOutput = opencode session list --format json 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Error "$($Script:Config.ErrorPrefix): opencode session list failed (exit $LASTEXITCODE)"
                return @()
            }

            $sessions = $jsonOutput | ConvertFrom-Json
            if ($null -eq $sessions) {
                return @()
            }

            # Normalize to array
            return @($sessions)
        }
        catch {
            Write-Error "$($Script:Config.ErrorPrefix): Failed to get session list — $_"
            return @()
        }
    }
}

function Get-SessionMessageCount {
    <#
    .SYNOPSIS
        Retrieves message count and agent list for a specific session.
    .DESCRIPTION
        Calls `opencode export <SessionId>` and parses the output to extract
        the total message count and list of agents used in the session.
    .PARAMETER SessionId
        The session identifier (e.g., "ses_abc123").
    .OUTPUTS
        System.Collections.Hashtable — Contains Keys: MessageCount (int), Agents (string[]).
        Returns $null on failure.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory, ValueFromPipelineByPropertyName)]
        [ValidateNotNullOrEmpty()]
        [string]$SessionId
    )

    process {
        try {
            $exportOutput = opencode export $SessionId 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Error "$($Script:Config.ErrorPrefix): opencode export failed for session $SessionId (exit $LASTEXITCODE)"
                return $null
            }

            # Parse message count from export output
            $messageCount = 0
            $agents = @()

            foreach ($line in $exportOutput) {
                if ($line -match 'Messages:\s*(\d+)') {
                    $messageCount = [int]$Matches[1]
                }
                if ($line -match 'Agents Used:\s*(.+)') {
                    $agents = ($Matches[1] -split ',\s*').Trim()
                }
            }

            return @{
                MessageCount = $messageCount
                Agents       = $agents
            }
        }
        catch {
            Write-Error "$($Script:Config.ErrorPrefix): Failed to get message count for session $SessionId — $_"
            return $null
        }
    }
}

function Get-SessionStatus {
    <#
    .SYNOPSIS
        Determines the lifecycle status of a session based on age and activity.
    .DESCRIPTION
        Classifies a session as Active, Stale, or Orphaned using configurable
        thresholds from session-config.psd1:
          - Active:  last activity within ActiveThresholdHours
          - Stale:   last activity older than StaleThresholdHours
          - Orphaned: message count below OrphanThreshold AND older than StaleThresholdHours
    .PARAMETER LastActivity
        DateTime of the session's last recorded activity.
    .PARAMETER MessageCount
        Total number of messages in the session.
    .OUTPUTS
        System.String — One of: "Active", "Stale", "Orphaned"
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNull()]
        [datetime]$LastActivity,

        [Parameter(Mandatory)]
        [ValidateRange(0, [int]::MaxValue)]
        [int]$MessageCount
    )

    process {
        try {
            $now = Get-Date
            $ageHours = ($now - $LastActivity).TotalHours

            $activeThreshold = $Script:Config.ActiveThresholdHours
            $staleThreshold  = $Script:Config.StaleThresholdHours
            $orphanThreshold = $Script:Config.OrphanThreshold

            if ($ageHours -le $activeThreshold) {
                return 'Active'
            }

            if ($MessageCount -lt $orphanThreshold -and $ageHours -gt $staleThreshold) {
                return 'Orphaned'
            }

            if ($ageHours -gt $staleThreshold) {
                return 'Stale'
            }

            # Between active and stale thresholds — still considered active
            return 'Active'
        }
        catch {
            Write-Error "$($Script:Config.ErrorPrefix): Failed to determine session status — $_"
            return 'Unknown'
        }
    }
}

# ── Module Exports ───────────────────────────────────────────────────────────
Export-ModuleMember -Function @(
    'Get-SessionList'
    'Get-SessionMessageCount'
    'Format-Agents'
    'Get-SessionStatus'
)
