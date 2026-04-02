# N-Xyme Catalyst - Auto-Recovery Script
# Automatically fixes common breakage patterns
# Usage: powershell -ExecutionPolicy Bypass -File scripts\auto-recover.ps1

param(
    [switch]$Aggressive,  # More thorough fixes
    [switch]$DryRun       # Show what would be fixed without doing it
)

$ErrorActionPreference = "SilentlyContinue"
$fixes = @()

function Fix-Apply($desc, $action) {
    if ($DryRun) {
        Write-Host "  [DRY RUN] Would fix: $desc" -ForegroundColor Cyan
    } else {
        Write-Host "  FIXING: $desc" -ForegroundColor Yellow
        & $action
    }
    $script:fixes += $desc
}

Write-Host "`n=== N-XYME AUTO-RECOVERY ===" -ForegroundColor Cyan
Write-Host "Scanning for common issues...`n" -ForegroundColor Gray

# ============================================
# FIX 1: MISSING .env FILE
# ============================================
$envPath = "D:\01_CODING\00_N-Xyme_CATALYST\.env"
if (-not (Test-Path $envPath)) {
    Fix-Apply "Create .env from .env.example" {
        Copy-Item "D:\01_CODING\00_N-Xyme_CATALYST\.env.example" $envPath
    }
}

# ============================================
# FIX 2: WRONG WIN PS PROFILE PATH
# ============================================
$winProfile = "C:\Users\N-Xyme\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
if (Test-Path $winProfile) {
    $content = Get-Content $winProfile -Raw
    if ($content -match "00_CODING") {
        Fix-Apply "Fix Win PS profile path (00_CODING → 01_CODING)" {
            $fixed = $content -replace "D:\\00_CODING", "D:\01_CODING"
            Set-Content $winProfile $fixed
        }
    }
}

# ============================================
# FIX 3: DUPLICATE PATH ENTRIES
# ============================================
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$entries = $userPath -split ';' | Where-Object { $_.Trim() -ne '' }
$unique = $entries | Select-Object -Unique
if ($entries.Count -ne $unique.Count) {
    Fix-Apply "Remove $($entries.Count - $unique.Count) duplicate PATH entries" {
        $cleaned = $unique -join ';'
        [Environment]::SetEnvironmentVariable('Path', $cleaned, 'User')
    }
}

# ============================================
# FIX 4: PM2 NOT RUNNING
# ============================================
$pm2Check = pm2 list --silent 2>$null
if (-not ($pm2Check -match "online")) {
    Fix-Apply "Start PM2 with all MCP servers" {
        Set-Location "D:\01_CODING\00_N-Xyme_CATALYST"
        pm2 start ecosystem.config.js 2>$null
        pm2 save 2>$null
    }
}

# ============================================
# FIX 5: GRAPHITI NEO4J PASSWORD
# ============================================
$graphitiCheck = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 3 2>$null
if ($graphitiCheck.StatusCode -ne 200) {
    # Check if it's a password issue
    $logs = Get-Content "C:\Users\N-Xyme\.pm2\logs\graphiti-mcp-error*.log" -Tail 20 -ErrorAction SilentlyContinue
    if ($logs -match "Unauthorized") {
        Fix-Apply "Restart Graphiti with correct Neo4j password" {
            pm2 delete graphiti-mcp 2>$null
            Set-Location "D:\01_CODING\00_N-Xyme_CATALYST"
            pm2 start ecosystem.config.js --only graphiti-mcp 2>$null
            pm2 save 2>$null
        }
    }
}

# ============================================
# FIX 6: STALE PM2 PROCESSES
# ============================================
$pm2Stale = pm2 list --silent 2>$null | Select-String "errored|stopped"
if ($pm2Stale) {
    Fix-Apply "Flush errored/stopped PM2 processes" {
        pm2 delete all 2>$null
        Set-Location "D:\01_CODING\00_N-Xyme_CATALYST"
        pm2 start ecosystem.config.js 2>$null
        pm2 save 2>$null
    }
}

# ============================================
# FIX 7: MISSING PM2 STARTUP (AGGRESSIVE ONLY)
# ============================================
if ($Aggressive) {
    $startupCheck = pm2 startup 2>$null
    if ($startupCheck -match "startup hook") {
        Fix-Apply "Configure PM2 auto-start on boot" {
            pm2 startup 2>$null
            pm2 save 2>$null
        }
    }
}

# ============================================
# SUMMARY
# ============================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "AUTO-RECOVERY COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($fixes.Count -eq 0) {
    Write-Host "No issues found. System is healthy." -ForegroundColor Green
} else {
    Write-Host "Applied $($fixes.Count) fixes:" -ForegroundColor Yellow
    foreach ($fix in $fixes) {
        Write-Host "  - $fix" -ForegroundColor Green
    }
    
    Write-Host "`nRunning verification..." -ForegroundColor Gray
    powershell -ExecutionPolicy Bypass -File "D:\01_CODING\00_N-Xyme_CATALYST\scripts\preflight-gate.ps1" -Quiet
}
