<#
.SYNOPSIS
    Scans for new cutting-edge technologies across multiple domains and generates a daily report.

.DESCRIPTION
    The Daily Tech Scout checks a configurable list of technology domains for new tools,
    frameworks, and patterns. It produces a dated markdown report in .sisyphus/tech-scout/
    and logs activity to .sisyphus/tech-scout.log.

    Domains include:
      - Vibe coding tools (Cursor, Windsurf, Bolt, Lovable, v0, etc.)
      - Local LLMs (Ollama, llama.cpp, vLLM, LM Studio, etc.)
      - Cloud LLMs (OpenAI, Anthropic, Google, Mistral, etc.)
      - AI coding assistants (Copilot, Cody, Continue, etc.)
      - Architecture patterns (event sourcing, CQRS, micro-frontends, etc.)
      - Developer tools (Bun, Deno, Tauri, etc.)
      - ADHD productivity tools (focus apps, time management, etc.)
      - MCP ecosystem (Model Context Protocol servers and tools)

    The script runs at most once per day (checks log for last run timestamp).
    Configuration is driven by .sisyphus/tech-scout-config.json.

    NOTE: This is a framework/placeholder. Actual web searches require integration
    with a search provider (GitHub API, web search, etc.). The structure is ready
    for extension via the Invoke-SearchProvider function.

.PARAMETER Force
    Skip the daily-run check and execute regardless of last run time.

.PARAMETER Prompt
    After generating the report, display a summary and ask the user if they want
    to explore any findings interactively.

.PARAMETER Domain
    Limit the scan to a specific domain ID (e.g., "vibe-coding", "local-llms").
    If omitted, all enabled domains are scanned.

.PARAMETER ConfigPath
    Path to the configuration JSON file. Defaults to .sisyphus/tech-scout-config.json.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File ./scripts/daily-tech-scout.ps1
    Runs the daily tech scout (skips if already run today).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File ./scripts/daily-tech-scout.ps1 -Force
    Forces a run even if already executed today.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File ./scripts/daily-tech-scout.ps1 -Prompt
    Runs the scout and prompts the user to explore findings interactively.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File ./scripts/daily-tech-scout.ps1 -Domain "local-llms"
    Scans only the local LLMs domain.

.OUTPUTS
    - Markdown report: .sisyphus/tech-scout/daily-{yyyy-MM-dd}.md
    - Log entries: .sisyphus/tech-scout.log
    - Console output with summary statistics

.NOTES
    Author:  Sisyphus (N-Xyme Catalyst)
    Version: 1.0.0
    Created: 2026-03-19
    Requires: PowerShell 5.1+, .sisyphus/tech-scout-config.json
#>

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$Prompt,
    [string]$Domain,
    [string]$ConfigPath = ".sisyphus/tech-scout-config.json"
)

# ─── Strict Mode ────────────────────────────────────────────────────────────────
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ─── Constants ──────────────────────────────────────────────────────────────────
$SCRIPT_VERSION   = "1.0.0"
$DATE_FORMAT      = "yyyy-MM-dd"
$TIMESTAMP_FORMAT = "yyyy-MM-dd HH:mm:ss"
$TODAY            = Get-Date -Format $DATE_FORMAT
$NOW              = Get-Date -Format $TIMESTAMP_FORMAT

# ─── Resolve Paths ──────────────────────────────────────────────────────────────
$RepoRoot   = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ConfigFile = Join-Path $RepoRoot $ConfigPath

# ─── Functions ───────────────────────────────────────────────────────────────────

function Write-Log {
    <#
    .SYNOPSIS
        Appends a timestamped entry to the scout log file.
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [ValidateSet("INFO", "WARN", "ERROR", "DEBUG")]
        [string]$Level = "INFO"
    )

    $logFile = $script:Config.settings.logFile
    if (-not $logFile) { $logFile = ".sisyphus/tech-scout.log" }
    $logPath = Join-Path $RepoRoot $logFile

    $logDir = Split-Path -Parent $logPath
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    $entry = "[$NOW] [$Level] $Message"
    Add-Content -Path $logPath -Value $entry
}

function Write-ScoutOutput {
    <#
    .SYNOPSIS
        Writes colored console output with consistent formatting.
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [ValidateSet("Header", "Domain", "Finding", "Success", "Warning", "Error", "Muted")]
        [string]$Style = "Muted"
    )

    $colors = @{
        Header  = @{ ForegroundColor = "Cyan";    BackgroundColor = $null }
        Domain  = @{ ForegroundColor = "Yellow";  BackgroundColor = $null }
        Finding = @{ ForegroundColor = "White";   BackgroundColor = $null }
        Success = @{ ForegroundColor = "Green";   BackgroundColor = $null }
        Warning = @{ ForegroundColor = "DarkYellow"; BackgroundColor = $null }
        Error   = @{ ForegroundColor = "Red";     BackgroundColor = $null }
        Muted   = @{ ForegroundColor = "DarkGray"; BackgroundColor = $null }
    }

    $c = $colors[$Style]
    Write-Host $Message @c
}

function Test-AlreadyRunToday {
    <#
    .SYNOPSIS
        Checks if the scout already ran today by inspecting the log file.
    #>
    $logFile = $script:Config.settings.logFile
    if (-not $logFile) { $logFile = ".sisyphus/tech-scout.log" }
    $logPath = Join-Path $RepoRoot $logFile

    if (-not (Test-Path $logPath)) {
        return $false
    }

    $lastRun = Get-Content $logPath -ErrorAction SilentlyContinue |
        Where-Object { $_ -match "^\[(\d{4}-\d{2}-\d{2})" } |
        ForEach-Object { [regex]::Match($_, "^\[(\d{4}-\d{2}-\d{2})").Groups[1].Value } |
        Sort-Object -Descending |
        Select-Object -First 1

    if (-not $lastRun) {
        return $false
    }

    return ($lastRun -eq $TODAY)
}

function Read-Config {
    <#
    .SYNOPSIS
        Loads and validates the tech-scout configuration JSON.
    #>
    if (-not (Test-Path $ConfigFile)) {
        Write-ScoutOutput "Config file not found: $ConfigFile" -Style Error
        Write-Log "Config file not found: $ConfigFile" -Level ERROR
        exit 1
    }

    try {
        $cfg = Get-Content $ConfigFile -Raw | ConvertFrom-Json
        Write-Log "Config loaded: $($cfg.domains.Count) domains" -Level DEBUG
        return $cfg
    }
    catch {
        Write-ScoutOutput "Failed to parse config: $_" -Style Error
        Write-Log "Config parse error: $_" -Level ERROR
        exit 1
    }
}

function Invoke-SearchProvider {
    <#
    .SYNOPSIS
        Placeholder for actual search integration. Returns simulated findings.

    .DESCRIPTION
        This function is the extension point for real search providers:
          - GitHub API (trending repos, new releases)
          - Web search (via Exa, Brave, or similar)
          - RSS feeds (dev blogs, changelogs)
          - npm/PyPI API (new packages, download trends)

        Currently returns placeholder data to demonstrate the framework.

    .PARAMETER Domain
        The domain configuration object from the config file.

    .PARAMETER SearchTerm
        The specific search term to query.

    .OUTPUTS
        Array of PSCustomObject with: Tool, Description, Source, Url, Stars, DateFound
    #>
    param(
        [Parameter(Mandatory)]
        [object]$Domain,

        [Parameter(Mandatory)]
        [string]$SearchTerm
    )

    # ── PLACEHOLDER: Replace with real search logic ──
    # Example integration points:
    #
    # GitHub API:
    #   $url = "https://api.github.com/search/repositories?q=$([Uri]::EscapeDataString($SearchTerm))&sort=stars&order=desc"
    #   $results = Invoke-RestMethod -Uri $url -Headers @{ Accept = "application/vnd.github.v3+json" }
    #
    # Web search (Exa/Brave):
    #   $url = "https://api.exa.ai/search?q=$([Uri]::EscapeDataString($SearchTerm))"
    #   $results = Invoke-RestMethod -Uri $url -Method Post -Body ($body | ConvertTo-Json) -ContentType "application/json"

    # For now, return a placeholder indicating this domain was scanned
    $placeholder = [PSCustomObject]@{
        Tool        = "[$($Domain.id)] $SearchTerm"
        Description = "Search pending — integrate a search provider to populate results"
        Source      = "placeholder"
        Url         = ""
        Stars       = 0
        DateFound   = $TODAY
    }

    return @($placeholder)
}

function Get-DomainFindings {
    <#
    .SYNOPSIS
        Scans a single domain for new technologies using all configured search terms.
    #>
    param(
        [Parameter(Mandatory)]
        [object]$Domain
    )

    $findings = @()
    $maxResults = $script:Config.settings.maxResultsPerDomain
    if (-not $maxResults) { $maxResults = 5 }

    foreach ($term in $Domain.searchTerms) {
        Write-Log "Searching: [$($Domain.id)] $term" -Level DEBUG

        $results = Invoke-SearchProvider -Domain $Domain -SearchTerm $term

        if ($results) {
            $findings += $results
        }

        # Respect rate limits (placeholder — adjust for real APIs)
        Start-Sleep -Milliseconds 200
    }

    # Deduplicate by tool name, keep first occurrence
    $seen = @{}
    $unique = @()
    foreach ($f in $findings) {
        if (-not $seen.ContainsKey($f.Tool)) {
            $seen[$f.Tool] = $true
            $unique += $f
        }
    }

    # Cap results
    return $unique | Select-Object -First $maxResults
}

function New-ReportMarkdown {
    <#
    .SYNOPSIS
        Generates the markdown report from collected findings.
    #>
    param(
        [Parameter(Mandatory)]
        [hashtable]$AllFindings
    )

    $totalNew = 0
    foreach ($d in $AllFindings.Values) {
        $totalNew += ($d | Where-Object { $_.Source -ne "placeholder" }).Count
    }

    $sb = [System.Text.StringBuilder]::new()

    # Header
    [void]$sb.AppendLine("# Tech Scout — $TODAY")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("**Generated:** $NOW")
    [void]$sb.AppendLine("**Version:** $SCRIPT_VERSION")
    [void]$sb.AppendLine("**Domains scanned:** $($AllFindings.Count)")
    [void]$sb.AppendLine("**New findings:** $totalNew")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("---")
    [void]$sb.AppendLine("")

    # Domain sections
    foreach ($domainId in ($AllFindings.Keys | Sort-Object)) {
        $domain = $script:Config.domains | Where-Object { $_.id -eq $domainId } | Select-Object -First 1
        $findings = $AllFindings[$domainId]

        $emoji = if ($domain.emoji) { $domain.emoji } else { "📦" }
        $name  = if ($domain.name) { $domain.name } else { $domainId }

        [void]$sb.AppendLine("## $emoji $name")
        [void]$sb.AppendLine("")

        if ($findings.Count -eq 0) {
            [void]$sb.AppendLine("_No new findings._")
            [void]$sb.AppendLine("")
            continue
        }

        foreach ($f in $findings) {
            if ($f.Url) {
                [void]$sb.AppendLine("- **$($f.Tool)** — $($f.Description) [$($f.Source)]($($f.Url))")
            }
            else {
                [void]$sb.AppendLine("- **$($f.Tool)** — $($f.Description)")
            }
        }

        [void]$sb.AppendLine("")
    }

    # Known tools reference
    [void]$sb.AppendLine("---")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("## 📋 Known Tools Reference")
    [void]$sb.AppendLine("")

    foreach ($domain in ($script:Config.domains | Where-Object { $_.enabled })) {
        $emoji = if ($domain.emoji) { $domain.emoji } else { "📦" }
        $tools = ($domain.knownTools | Sort-Object) -join ", "
        [void]$sb.AppendLine("- **$emoji $($domain.name):** $tools")
    }

    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("---")
    [void]$sb.AppendLine("_Generated by daily-tech-scout.ps1 v$SCRIPT_VERSION_")

    return $sb.ToString()
}

function Save-Report {
    <#
    .SYNOPSIS
        Writes the markdown report to the output directory.
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Markdown
    )

    $outputDir = $script:Config.settings.outputDir
    if (-not $outputDir) { $outputDir = ".sisyphus/tech-scout" }
    $outputPath = Join-Path $RepoRoot $outputDir

    if (-not (Test-Path $outputPath)) {
        New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
        Write-Log "Created output directory: $outputPath"
    }

    $reportFile = Join-Path $outputPath "daily-$TODAY.md"
    $Markdown | Set-Content -Path $reportFile -Encoding UTF8

    Write-Log "Report saved: $reportFile"
    return $reportFile
}

function Show-InteractivePrompt {
    <#
    .SYNOPSIS
        Displays findings summary and prompts user for exploration.
    #>
    param(
        [Parameter(Mandatory)]
        [hashtable]$AllFindings,

        [Parameter(Mandatory)]
        [string]$ReportPath
    )

    Write-ScoutOutput "" -Style Muted
    Write-ScoutOutput "═══════════════════════════════════════════════════" -Style Header
    Write-ScoutOutput "  TECH SCOUT SUMMARY — $TODAY" -Style Header
    Write-ScoutOutput "═══════════════════════════════════════════════════" -Style Header
    Write-ScoutOutput "" -Style Muted

    $totalFindings = 0
    foreach ($domainId in ($AllFindings.Keys | Sort-Object)) {
        $domain = $script:Config.domains | Where-Object { $_.id -eq $domainId } | Select-Object -First 1
        $findings = $AllFindings[$domainId]
        $emoji = if ($domain.emoji) { $domain.emoji } else { "📦" }
        $name  = if ($domain.name) { $domain.name } else { $domainId }

        $realFindings = $findings | Where-Object { $_.Source -ne "placeholder" }
        $totalFindings += $realFindings.Count

        if ($realFindings.Count -gt 0) {
            Write-ScoutOutput "  $emoji $($name): $($realFindings.Count) new" -Style Domain
            foreach ($f in $realFindings) {
                Write-ScoutOutput "    → $($f.Tool)" -Style Finding
            }
        }
        else {
            Write-ScoutOutput "  $emoji $($name): —" -Style Muted
        }
    }

    Write-ScoutOutput "" -Style Muted
    Write-ScoutOutput "  Total: $totalFindings new technologies found" -Style Success
    Write-ScoutOutput "  Report: $ReportPath" -Style Muted
    Write-ScoutOutput "" -Style Muted

    if ($totalFindings -eq 0) {
        Write-ScoutOutput "  No new findings to explore. Check back tomorrow!" -Style Warning
        return
    }

    $response = Read-Host "  Want to explore any of these? (y/n)"
    if ($response -match '^[Yy]') {
        Write-ScoutOutput "" -Style Muted
        Write-ScoutOutput "  Opening report..." -Style Success
        Write-ScoutOutput "  Tip: Use 'code `"$ReportPath`"' to open in VS Code" -Style Muted

        # Try to open in default editor
        try {
            Start-Process $ReportPath -ErrorAction SilentlyContinue
        }
        catch {
            Write-ScoutOutput "  Could not open automatically. Open manually: $ReportPath" -Style Warning
        }
    }
}

# ─── Main ────────────────────────────────────────────────────────────────────────

function Main {
    Write-ScoutOutput "" -Style Muted
    Write-ScoutOutput "┌─────────────────────────────────────────────┐" -Style Header
    Write-ScoutOutput "│  DAILY TECH SCOUT v$SCRIPT_VERSION                    │" -Style Header
    Write-ScoutOutput "│  Scanning for cutting-edge technologies...  │" -Style Header
    Write-ScoutOutput "└─────────────────────────────────────────────┘" -Style Header
    Write-ScoutOutput "" -Style Muted

    # Load config
    $script:Config = Read-Config
    Write-Log "Tech scout started (Force=$Force, Prompt=$Prompt, Domain=$Domain)"

    # Daily run check
    if (-not $Force) {
        if (Test-AlreadyRunToday) {
            Write-ScoutOutput "Already run today. Use -Force to re-run." -Style Warning
            Write-Log "Skipped — already run today" -Level INFO
            exit 0
        }
    }

    # Filter domains
    $domainsToScan = $script:Config.domains | Where-Object { $_.enabled -eq $true }
    if ($Domain) {
        $domainsToScan = $domainsToScan | Where-Object { $_.id -eq $Domain }
        if (-not $domainsToScan) {
            Write-ScoutOutput "Domain '$Domain' not found or not enabled." -Style Error
            Write-Log "Domain not found: $Domain" -Level ERROR
            exit 1
        }
    }

    Write-ScoutOutput "  Domains to scan: $($domainsToScan.Count)" -Style Muted
    Write-ScoutOutput "" -Style Muted

    # Scan each domain
    $allFindings = @{}
    $domainIndex = 0

    foreach ($d in $domainsToScan) {
        $domainIndex++
        $emoji = if ($d.emoji) { $d.emoji } else { "📦" }
        $name  = if ($d.name) { $d.name } else { $d.id }

        Write-ScoutOutput "  [$domainIndex/$($domainsToScan.Count)] Scanning $emoji $name..." -Style Domain

        try {
            $findings = Get-DomainFindings -Domain $d
            $allFindings[$d.id] = $findings

            $realCount = ($findings | Where-Object { $_.Source -ne "placeholder" }).Count
            if ($realCount -gt 0) {
                Write-ScoutOutput "           Found $realCount new items" -Style Success
            }
            else {
                Write-ScoutOutput "           No new items (placeholder mode)" -Style Muted
            }
        }
        catch {
            Write-ScoutOutput "           Error: $_" -Style Error
            Write-Log "Error scanning domain $($d.id): $_" -Level ERROR
            $allFindings[$d.id] = @()
        }
    }

    Write-ScoutOutput "" -Style Muted

    # Generate and save report
    $markdown = New-ReportMarkdown -AllFindings $allFindings
    $reportPath = Save-Report -Markdown $markdown

    # Calculate totals
    $totalNew = 0
    foreach ($d in $allFindings.Values) {
        $totalNew += ($d | Where-Object { $_.Source -ne "placeholder" }).Count
    }

    # Output summary
    Write-ScoutOutput "  ═══════════════════════════════════════════" -Style Header
    Write-ScoutOutput "  $totalNew new technologies found." -Style Success
    Write-ScoutOutput "  Report: $reportPath" -Style Muted
    Write-ScoutOutput "  Run /tech-scout to review." -Style Muted
    Write-ScoutOutput "  ═══════════════════════════════════════════" -Style Header
    Write-ScoutOutput "" -Style Muted

    Write-Log "Tech scout completed — $totalNew findings across $($allFindings.Count) domains"

    # Interactive prompt mode
    if ($Prompt) {
        Show-InteractivePrompt -AllFindings $allFindings -ReportPath $reportPath
    }
}

# ─── Entry Point ─────────────────────────────────────────────────────────────────
Main
