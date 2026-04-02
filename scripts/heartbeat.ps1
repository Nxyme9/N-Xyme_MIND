<#
.SYNOPSIS
    Lightweight heartbeat health checker for N-Xyme Catalyst workspace.

.DESCRIPTION
    Performs quick syntax and environment checks across the workspace:
      1. PowerShell (.ps1) script syntax validation
      2. TypeScript (.ts) script syntax validation
      3. OpenCode CLI availability
      4. .akasha/ directory presence
      5. .sisyphus/handoffs/ directory presence
      6. Disk space check (warns if < 1 GB free)

    Results are written to .sisyphus/heartbeat.json and displayed as a
    PASS/FAIL table. Exit code 0 = all pass, 1 = any failure.

.PARAMETER WorkspaceRoot
    Root path of the workspace. Defaults to the parent of the scripts directory.

.PARAMETER JsonOutputPath
    Path to write the JSON results file. Defaults to .sisyphus/heartbeat.json
    under the workspace root.

.PARAMETER MinDiskSpaceGB
    Minimum free disk space in GB before triggering a warning. Default: 1.

.EXAMPLE
    .\heartbeat.ps1
    Run all checks with defaults.

.EXAMPLE
    .\heartbeat.ps1 -WorkspaceRoot "D:\projects\catalyst" -MinDiskSpaceGB 2
    Run checks against a custom workspace root with a 2 GB disk threshold.

.OUTPUTS
    PSCustomObject[] — array of check results with Check, Status, Details.
    Also writes .sisyphus/heartbeat.json.

.NOTES
    Author : N-Xyme Catalyst Automation
    Version: 1.0.0
    Requires: PowerShell 5.1+, Node.js (for .ts checks)
#>

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$JsonOutputPath,

    [Parameter()]
    [ValidateRange(0.1, 100)]
    [double]$MinDiskSpaceGB = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Helpers ──────────────────────────────────────────────────────────────────

function New-CheckResult {
    <#
    .SYNOPSIS
        Creates a standardized check result object.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Check,

        [Parameter(Mandatory)]
        [ValidateSet('PASS', 'FAIL', 'WARN')]
        [string]$Status,

        [Parameter(Mandatory)]
        [string]$Details
    )

    [PSCustomObject]@{
        Check   = $Check
        Status  = $Status
        Details = $Details
    }
}

# ── Resolve paths ────────────────────────────────────────────────────────────

if (-not $JsonOutputPath) {
    $JsonOutputPath = Join-Path $WorkspaceRoot '.sisyphus\heartbeat.json'
}

$results = [System.Collections.Generic.List[PSCustomObject]]::new()

# ── Check 1: PowerShell script syntax ────────────────────────────────────────

try {
    $ps1Files = @(Get-ChildItem -Path $WorkspaceRoot -Filter '*.ps1' -Recurse -File -ErrorAction Stop |
        Where-Object { $_.FullName -notmatch '\\node_modules\\|\\.git\\' })

    $parseErrors = @()
    foreach ($file in $ps1Files) {
        $tokens   = $null
        $astError = $null
        $null = [System.Management.Automation.Language.Parser]::ParseFile(
            $file.FullName, [ref]$tokens, [ref]$astError
        )
        if ($astError.Count -gt 0) {
            $parseErrors += "$($file.Name): $($astError[0].Message)"
        }
    }

    if ($parseErrors.Count -eq 0) {
        $results.Add((New-CheckResult -Check 'ps1-syntax' -Status 'PASS' -Details "$($ps1Files.Count) scripts OK"))
    } else {
        $detail = ($parseErrors | Select-Object -First 3) -join '; '
        if ($parseErrors.Count -gt 3) { $detail += "; +$($parseErrors.Count - 3) more" }
        $results.Add((New-CheckResult -Check 'ps1-syntax' -Status 'FAIL' -Details $detail))
    }
}
catch {
    $results.Add((New-CheckResult -Check 'ps1-syntax' -Status 'FAIL' -Details "ERROR: [ps1-syntax] $($_.Exception.Message)"))
}

# ── Check 2: TypeScript script syntax ────────────────────────────────────────

try {
    $tsFiles = @(Get-ChildItem -Path $WorkspaceRoot -Filter '*.ts' -Recurse -File -ErrorAction Stop |
        Where-Object { $_.FullName -notmatch '\\node_modules\\|\\.git\\|\\dist\\' })

    $tscAvailable = $false
    try { $null = & tsc --version 2>&1; $tscAvailable = $true } catch {}

    if (-not $tscAvailable) {
        $results.Add((New-CheckResult -Check 'ts-syntax' -Status 'WARN' -Details 'tsc not found — skipped'))
    }
    elseif ($tsFiles.Count -eq 0) {
        $results.Add((New-CheckResult -Check 'ts-syntax' -Status 'PASS' -Details '0 .ts files found'))
    }
    else {
        $tsErrors = @()
        foreach ($file in $tsFiles) {
            $output = & tsc --noEmit --strict --target ES2020 --moduleResolution node $file.FullName 2>&1
            if ($LASTEXITCODE -ne 0) {
                $tsErrors += "$($file.Name): $($output | Select-Object -First 1)"
            }
        }

        if ($tsErrors.Count -eq 0) {
            $results.Add((New-CheckResult -Check 'ts-syntax' -Status 'PASS' -Details "$($tsFiles.Count) scripts OK"))
        } else {
            $detail = ($tsErrors | Select-Object -First 3) -join '; '
            if ($tsErrors.Count -gt 3) { $detail += "; +$($tsErrors.Count - 3) more" }
            $results.Add((New-CheckResult -Check 'ts-syntax' -Status 'FAIL' -Details $detail))
        }
    }
}
catch {
    $results.Add((New-CheckResult -Check 'ts-syntax' -Status 'FAIL' -Details "ERROR: [ts-syntax] $($_.Exception.Message)"))
}

# ── Check 3: OpenCode CLI availability ───────────────────────────────────────

try {
    $ocPath = Get-Command 'opencode' -ErrorAction SilentlyContinue
    if ($ocPath) {
        $version = (& opencode --version 2>&1 | Select-Object -First 1).ToString().Trim()
        $results.Add((New-CheckResult -Check 'opencode-cli' -Status 'PASS' -Details "Found: $version"))
    } else {
        $results.Add((New-CheckResult -Check 'opencode-cli' -Status 'FAIL' -Details 'ERROR: [opencode-cli] opencode not in PATH'))
    }
}
catch {
    $results.Add((New-CheckResult -Check 'opencode-cli' -Status 'FAIL' -Details "ERROR: [opencode-cli] $($_.Exception.Message)"))
}

# ── Check 4: .akasha/ directories ────────────────────────────────────────────

try {
    $akashaDirs = @(Get-ChildItem -Path $WorkspaceRoot -Directory -Filter '.akasha' -Recurse -ErrorAction Stop |
        Where-Object { $_.FullName -notmatch '\\node_modules\\|\\.git\\' })

    if ($akashaDirs.Count -gt 0) {
        $paths = ($akashaDirs | ForEach-Object {
            $_.FullName.Replace($WorkspaceRoot, '.')
        }) -join ', '
        $results.Add((New-CheckResult -Check 'akasha-dirs' -Status 'PASS' -Details "$($akashaDirs.Count) found: $paths"))
    } else {
        $results.Add((New-CheckResult -Check 'akasha-dirs' -Status 'WARN' -Details 'No .akasha/ directories found'))
    }
}
catch {
    $results.Add((New-CheckResult -Check 'akasha-dirs' -Status 'FAIL' -Details "ERROR: [akasha-dirs] $($_.Exception.Message)"))
}

# ── Check 5: .sisyphus/handoffs/ directory ───────────────────────────────────

try {
    $handoffsPath = Join-Path $WorkspaceRoot '.sisyphus\handoffs'
    if (Test-Path -Path $handoffsPath -PathType Container) {
        $fileCount = @(Get-ChildItem -Path $handoffsPath -File -ErrorAction SilentlyContinue).Count
        $results.Add((New-CheckResult -Check 'handoffs-dir' -Status 'PASS' -Details "Exists ($fileCount files)"))
    } else {
        $results.Add((New-CheckResult -Check 'handoffs-dir' -Status 'FAIL' -Details 'ERROR: [handoffs-dir] .sisyphus\handoffs\ not found'))
    }
}
catch {
    $results.Add((New-CheckResult -Check 'handoffs-dir' -Status 'FAIL' -Details "ERROR: [handoffs-dir] $($_.Exception.Message)"))
}

# ── Check 6: Disk space ─────────────────────────────────────────────────────

try {
    $drive = (Get-Item $WorkspaceRoot).PSDrive
    if (-not $drive) {
        # Fallback: resolve drive letter from path
        $driveLetter = $WorkspaceRoot.Substring(0, 1)
        $drive = Get-PSDrive -Name $driveLetter -ErrorAction Stop
    }

    $freeGB = [math]::Round($drive.Free / 1GB, 2)

    if ($freeGB -lt $MinDiskSpaceGB) {
        $results.Add((New-CheckResult -Check 'disk-space' -Status 'FAIL' -Details "ERROR: [disk-space] Only ${freeGB} GB free (threshold: ${MinDiskSpaceGB} GB)"))
    } elseif ($freeGB -lt ($MinDiskSpaceGB * 5)) {
        $results.Add((New-CheckResult -Check 'disk-space' -Status 'WARN' -Details "${freeGB} GB free (low)"))
    } else {
        $results.Add((New-CheckResult -Check 'disk-space' -Status 'PASS' -Details "${freeGB} GB free"))
    }
}
catch {
    $results.Add((New-CheckResult -Check 'disk-space' -Status 'FAIL' -Details "ERROR: [disk-space] $($_.Exception.Message)"))
}

# ── Write JSON output ────────────────────────────────────────────────────────

try {
    $jsonDir = Split-Path -Parent $JsonOutputPath
    if (-not (Test-Path $jsonDir)) {
        New-Item -ItemType Directory -Path $jsonDir -Force | Out-Null
    }

    $payload = @{
        timestamp = (Get-Date).ToUniversalTime().ToString('o')
        workspace = $WorkspaceRoot
        summary   = @{
            total  = $results.Count
            passed = @($results | Where-Object Status -eq 'PASS').Count
            warned = @($results | Where-Object Status -eq 'WARN').Count
            failed = @($results | Where-Object Status -eq 'FAIL').Count
        }
        checks    = $results
    }

    $payload | ConvertTo-Json -Depth 5 | Set-Content -Path $JsonOutputPath -Encoding UTF8 -ErrorAction Stop
}
catch {
    Write-Warning "Failed to write heartbeat JSON: $($_.Exception.Message)"
}

# ── Output table ─────────────────────────────────────────────────────────────

Write-Host ''
$results | Format-Table -Property @(
    @{ Label = 'Check';   Expression = { $_.Check };   Width = 16 }
    @{ Label = 'Status';  Expression = {
        switch ($_.Status) {
            'PASS' { "`e[32mPASS`e[0m" }
            'WARN' { "`e[33mWARN`e[0m" }
            'FAIL' { "`e[31mFAIL`e[0m" }
        }
    }; Width = 8 }
    @{ Label = 'Details'; Expression = { $_.Details } }
) -AutoSize -Wrap

# ── Summary line ─────────────────────────────────────────────────────────────

$failCount = @($results | Where-Object Status -eq 'FAIL').Count
$warnCount = @($results | Where-Object Status -eq 'WARN').Count

if ($failCount -gt 0) {
    Write-Host "`e[31m$failCount check(s) FAILED, $warnCount warning(s)`e[0m" -ForegroundColor Red
} elseif ($warnCount -gt 0) {
    Write-Host "`e[33mAll checks passed with $warnCount warning(s)`e[0m" -ForegroundColor Yellow
} else {
    Write-Host "`e[32mAll checks PASSED`e[0m" -ForegroundColor Green
}

Write-Host "Results written to: $JsonOutputPath`n"

# ── Exit code ────────────────────────────────────────────────────────────────

exit $(if ($failCount -gt 0) { 1 } else { 0 })
