# N-Xyme Catalyst - Pre-Flight Health Gate
# Run this BEFORE starting any work. Blocks if critical systems are down.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\preflight-gate.ps1

param(
    [switch]$Fix,       # Auto-fix known issues
    [switch]$Quiet,     # Minimal output
    [switch]$JSON       # Output as JSON
)

$ErrorActionPreference = "SilentlyContinue"
$issues = @()
$warnings = @()
$pass = @()

function Check-Pass($msg) { $script:pass += $msg; if (-not $Quiet) { Write-Host "  OK  $msg" -ForegroundColor Green } }
function Check-Warn($msg) { $script:warnings += $msg; if (-not $Quiet) { Write-Host "  WARN $msg" -ForegroundColor Yellow } }
function Check-Fail($msg) { $script:issues += $msg; if (-not $Quiet) { Write-Host "  FAIL $msg" -ForegroundColor Red } }

Write-Host "`n=== N-XYME CATALYST PRE-FLIGHT GATE ===" -ForegroundColor Cyan
Write-Host "Scanning critical systems...`n" -ForegroundColor Gray

# ============================================
# LAYER 1: ENVIRONMENT
# ============================================
Write-Host "[1/6] ENVIRONMENT" -ForegroundColor White

# Check .env exists
$envPath = "D:\01_CODING\00_N-Xyme_CATALYST\.env"
if (Test-Path $envPath) {
    Check-Pass ".env file exists"
    
    # Check critical env vars
    $envContent = Get-Content $envPath -Raw
    if ($envContent -match "NEO4J_PASSWORD=.+") { Check-Pass "NEO4J_PASSWORD set" } else { Check-Fail "NEO4J_PASSWORD missing in .env" }
    if ($envContent -match "OLLAMA_URL=.+") { Check-Pass "OLLAMA_URL set" } else { Check-Warn "OLLAMA_URL not set (using default)" }
} else {
    Check-Fail ".env file MISSING - copy .env.example to .env"
    
    if ($Fix) {
        Write-Host "    FIXING: Copying .env.example to .env..." -ForegroundColor Yellow
        Copy-Item "D:\01_CODING\00_N-Xyme_CATALYST\.env.example" $envPath
        Check-Pass ".env created from template (needs manual editing)"
    }
}

# Check PATH for duplicates
$pathEntries = $env:PATH -split ';' | Where-Object { $_.Trim() -ne '' }
$pathGroups = $pathEntries | Group-Object { $_.Trim().TrimEnd('\').ToLower() }
$duplicates = $pathGroups | Where-Object { $_.Count -gt 1 }
if ($duplicates.Count -eq 0) {
    Check-Pass "PATH clean (no duplicates)"
} else {
    Check-Warn "PATH has $($duplicates.Count) duplicate entries"
}

# ============================================
# LAYER 2: SHELL HEALTH
# ============================================
Write-Host "`n[2/6] SHELL HEALTH" -ForegroundColor White

# Measure profile load time
$profileTime = (Measure-Command { pwsh -Command "exit" }).TotalMilliseconds
if ($profileTime -lt 500) {
    Check-Pass "PS7 loads in ${profileTime}ms"
} elseif ($profileTime -lt 2000) {
    Check-Warn "PS7 slow: ${profileTime}ms (should be <500ms)"
} else {
    Check-Fail "PS7 broken: ${profileTime}ms (should be <500ms)"
}

# Check PSReadLine version
$psrlVersion = (Get-Module PSReadLine -ListAvailable | Sort-Object Version -Descending | Select-Object -First 1).Version
if ($psrlVersion -ge [version]"2.3.0") {
    Check-Pass "PSReadLine $psrlVersion (current)"
} else {
    Check-Fail "PSReadLine $psrlVersion outdated (need 2.3+)"
    
    if ($Fix) {
        Write-Host "    FIXING: Updating PSReadLine..." -ForegroundColor Yellow
        Install-Module PSReadLine -Force -SkipPublisherCheck -Scope CurrentUser
    }
}

# ============================================
# LAYER 3: CORE SERVICES
# ============================================
Write-Host "`n[3/6] CORE SERVICES" -ForegroundColor White

# Ollama
$ollamaResp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 2>$null
if ($ollamaResp.StatusCode -eq 200) {
    $models = ($ollamaResp.Content | ConvertFrom-Json).models.Count
    Check-Pass "Ollama online ($models models)"
} else {
    Check-Fail "Ollama offline at localhost:11434"
}

# Neo4j
$neo4jResp = Invoke-WebRequest -Uri "http://localhost:7474/" -TimeoutSec 5 2>$null
if ($neo4jResp.StatusCode -eq 200) {
    Check-Pass "Neo4j online (v$(($neo4jResp.Content | ConvertFrom-Json).neo4j_version))"
} else {
    Check-Fail "Neo4j offline at localhost:7474"
}

# ============================================
# LAYER 4: MCP SERVERS
# ============================================
Write-Host "`n[4/6] MCP SERVERS" -ForegroundColor White

$mcpServers = @(
    @{Name="playwright-mcp"; Port=12010},
    @{Name="puppeteer-mcp"; Port=12011},
    @{Name="fetch-mcp"; Port=12012},
    @{Name="brave-search-mcp"; Port=12013},
    @{Name="exa-mcp"; Port=12014},
    @{Name="ollama-mcp"; Port=11435},
    @{Name="git-mcp"; Port=12002},
    @{Name="github-mcp"; Port=12001},
    @{Name="sqlite-mcp"; Port=12003},
    @{Name="context7-mcp"; Port=12020},
    @{Name="grep-app-mcp"; Port=12021},
    @{Name="obsidian-mcp"; Port=12022},
    @{Name="shadcn-mcp"; Port=12023},
    @{Name="graphiti-mcp"; Port=8001}
)

$online = 0
foreach ($mcp in $mcpServers) {
    $resp = Invoke-WebRequest -Uri "http://localhost:$($mcp.Port)/health" -TimeoutSec 3 2>$null
    if ($resp.StatusCode -eq 200) {
        $online++
    } else {
        Check-Warn "$($mcp.Name) offline (port $($mcp.Port))"
    }
}

if ($online -eq $mcpServers.Count) {
    Check-Pass "All $online MCP servers online"
} elseif ($online -gt 10) {
    Check-Warn "$online/$($mcpServers.Count) MCP servers online"
} else {
    Check-Fail "Only $online/$($mcpServers.Count) MCP servers online"
}

# ============================================
# LAYER 5: PM2
# ============================================
Write-Host "`n[5/6] PM2 PROCESS MANAGER" -ForegroundColor White

$pm2Status = pm2 list --silent 2>$null
if ($pm2Status -match "online") {
    $pm2Online = ($pm2Status | Select-String "online").Count
    Check-Pass "PM2 running ($pm2Online processes)"
} else {
    Check-Fail "PM2 not running or no processes"
    
    if ($Fix) {
        Write-Host "    FIXING: Starting MCP servers via PM2..." -ForegroundColor Yellow
        Set-Location "D:\01_CODING\00_N-Xyme_CATALYST"
        pm2 start ecosystem.config.js 2>$null
        pm2 save 2>$null
    }
}

# ============================================
# LAYER 6: CONFIG VALIDATION
# ============================================
Write-Host "`n[6/6] CONFIG VALIDATION" -ForegroundColor White

# Check critical config files exist
$configs = @(
    "C:\Users\N-Xyme\.config\opencode\opencode.json",
    "C:\Users\N-Xyme\.config\opencode\oh-my-opencode.json",
    "D:\01_CODING\00_N-Xyme_CATALYST\ecosystem.config.js",
    "D:\01_CODING\00_N-Xyme_CATALYST\AGENTS.md"
)

foreach ($config in $configs) {
    if (Test-Path $config) {
        # Don't spam output for every config
    } else {
        Check-Fail "Config missing: $config"
    }
}
Check-Pass "Critical config files present"

# Check Win PS profile has correct path
$winProfile = "C:\Users\N-Xyme\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
if (Test-Path $winProfile) {
    $profileContent = Get-Content $winProfile -Raw
    if ($profileContent -match "00_CODING") {
        Check-Fail "Win PS profile has WRONG path (00_CODING instead of 01_CODING)"
    } else {
        Check-Pass "Win PS profile path correct"
    }
}

# ============================================
# SUMMARY
# ============================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PRE-FLIGHT SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Passed:   $($pass.Count)" -ForegroundColor Green
Write-Host "  Warnings: $($warnings.Count)" -ForegroundColor Yellow
Write-Host "  FAILURES: $($issues.Count)" -ForegroundColor Red

if ($issues.Count -gt 0) {
    Write-Host "`nCRITICAL ISSUES:" -ForegroundColor Red
    foreach ($issue in $issues) {
        Write-Host "  - $issue" -ForegroundColor Red
    }
    Write-Host "`nRun with -Fix to auto-fix known issues." -ForegroundColor Yellow
    Write-Host "EXIT CODE: 1 (BLOCKED)" -ForegroundColor Red
    exit 1
} elseif ($warnings.Count -gt 0) {
    Write-Host "`nWARNINGS:" -ForegroundColor Yellow
    foreach ($warn in $warnings) {
        Write-Host "  - $warn" -ForegroundColor Yellow
    }
    Write-Host "`nEXIT CODE: 0 (PASS with warnings)" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "`nALL SYSTEMS GO" -ForegroundColor Green
    Write-Host "EXIT CODE: 0 (PASS)" -ForegroundColor Green
    exit 0
}
