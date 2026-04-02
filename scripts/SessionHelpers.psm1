<#
.SYNOPSIS
    Shared helper functions for OpenCode session management scripts.

.DESCRIPTION
    Provides reusable functions for session status classification and agent
    formatting across detect-orphans.ps1, session-dashboard.ps1, and related
    scripts. Import via: Import-Module .\SessionHelpers.psm1
#>

Set-StrictMode -Version Latest

function Get-SessionStatus {
    <#
    .SYNOPSIS
        Classifies a session as Active, Stale, or Orphaned based on message count and activity.
    .PARAMETER MessageCount
        Number of messages in the session.
    .PARAMETER LastActive
        DateTime of the last activity. If not provided, uses current time.
    .PARAMETER OrphanThreshold
        Message count below which a session is considered orphaned. Default: 5
    .PARAMETER StaleHours
        Hours of inactivity before a session is marked Stale. Default: 1
    .PARAMETER StaleCriticalHours
        Hours of inactivity before a session is marked Stale>24h. Default: 24
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [int]$MessageCount,

        [datetime]$LastActive,

        [int]$OrphanThreshold = 5,

        [int]$StaleHours = 1,

        [int]$StaleCriticalHours = 24
    )

    if ($MessageCount -lt $OrphanThreshold) { return "[ORPHAN]" }

    if ($LastActive) {
        $hoursSinceActive = ((Get-Date) - $LastActive).TotalHours
        if ($hoursSinceActive -gt $StaleCriticalHours) { return "[STALE>24h]" }
        elseif ($hoursSinceActive -gt $StaleHours) { return "[STALE]" }
    }

    return "[ACTIVE]"
}

function Format-Agents {
    <#
    .SYNOPSIS
        Formats an agents array/string into a comma-separated string.
    .PARAMETER Agents
        Agent list (array, string, or null).
    #>
    [CmdletBinding()]
    param($Agents)

    if ($null -eq $Agents) { return "none" }
    if ($Agents -is [Array]) {
        $filtered = $Agents | Where-Object { $_ -and $_.ToString().Trim() -ne '' }
        if ($filtered.Count -eq 0) { return "none" }
        return ($filtered -join ", ")
    }
    $str = $Agents.ToString()
    if ([string]::IsNullOrWhiteSpace($str)) { return "none" }
    return $str
}

Export-ModuleMember -Function Get-SessionStatus, Format-Agents
