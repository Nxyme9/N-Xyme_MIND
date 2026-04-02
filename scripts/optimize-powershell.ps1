# PowerShell Cleanup & Optimization Script
# Run this to diagnose and fix slow terminal startup

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  PowerShell Startup Optimizer" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Step 1: Measure baseline startup time
Write-Host "[1/6] Measuring baseline startup time..." -ForegroundColor Yellow
$baseline = Measure-Command { powershell -NoProfile -Command "Write-Host 'OK'" }
Write-Host "  Baseline (no profile): $([math]::Round($baseline.TotalMilliseconds))ms" -ForegroundColor Gray

$withProfile = Measure-Command { powershell -Command "Write-Host 'OK'" }
Write-Host "  With profile: $([math]::Round($withProfile.TotalMilliseconds))ms" -ForegroundColor Gray

$difference = $withProfile.TotalMilliseconds - $baseline.TotalMilliseconds
if ($difference -gt 500) {
    Write-Host "  [WARNING] Profile adds $([math]::Round($difference))ms to startup!" -ForegroundColor Red
} else {
    Write-Host "  [OK] Profile overhead is acceptable" -ForegroundColor Green
}

# Step 2: Check for Oh-My-Posh
Write-Host ""
Write-Host "[2/6] Checking Oh-My-Posh..." -ForegroundColor Yellow
if (Get-Command oh-my-posh -ErrorAction SilentlyContinue) {
    $ompVersion = oh-my-posh version
    Write-Host "  [FOUND] Oh-My-Posh $ompVersion" -ForegroundColor Yellow
    Write-Host "  [INFO] This can add 200-500ms to startup" -ForegroundColor Gray
    Write-Host "  [ACTION] Consider using a minimal theme or disabling" -ForegroundColor Gray
} else {
    Write-Host "  [OK] Oh-My-Posh not installed" -ForegroundColor Green
}

# Step 3: Check loaded modules
Write-Host ""
Write-Host "[3/6] Checking loaded modules..." -ForegroundColor Yellow
$modules = Get-Module
Write-Host "  Loaded modules: $($modules.Count)" -ForegroundColor Gray
foreach ($mod in $modules) {
    Write-Host "    - $($mod.Name) v$($mod.Version)" -ForegroundColor Gray
}

# Step 4: Check available modules (potential auto-import)
Write-Host ""
Write-Host "[4/6] Checking available modules..." -ForegroundColor Yellow
$available = Get-Module -ListAvailable
Write-Host "  Available modules: $($available.Count)" -ForegroundColor Gray

$heavyModules = $available | Where-Object { $_.Name -match "Azure|ActiveDirectory|Exchange|Teams|SharePoint" }
if ($heavyModules) {
    Write-Host "  [WARNING] Heavy modules detected:" -ForegroundColor Yellow
    foreach ($mod in $heavyModules) {
        Write-Host "    - $($mod.Name)" -ForegroundColor Yellow
    }
}

# Step 5: Check profile files
Write-Host ""
Write-Host "[5/6] Checking profile files..." -ForegroundColor Yellow
$profilePaths = @(
    $PROFILE.AllUsersAllHosts,
    $PROFILE.AllUsersCurrentHost,
    $PROFILE.CurrentUserAllHosts,
    $PROFILE.CurrentUserCurrentHost
)

foreach ($path in $profilePaths) {
    if (Test-Path $path) {
        $lines = (Get-Content $path | Measure-Object -Line).Lines
        Write-Host "  [FOUND] $path ($lines lines)" -ForegroundColor Yellow
    } else {
        Write-Host "  [OK] $path (not found)" -ForegroundColor Gray
    }
}

# Step 6: Recommendations
Write-Host ""
Write-Host "[6/6] Recommendations..." -ForegroundColor Yellow

if ($withProfile.TotalMilliseconds -gt 1000) {
    Write-Host ""
    Write-Host "  ════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host "  SLOW STARTUP DETECTED!" -ForegroundColor Red
    Write-Host "  ════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Fixes:" -ForegroundColor Yellow
    Write-Host "  1. Disable Oh-My-Posh or use minimal theme" -ForegroundColor Gray
    Write-Host "  2. Remove heavy module imports from profile" -ForegroundColor Gray
    Write-Host "  3. Add Windows Defender exclusion for PowerShell" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Quick fix - run this command:" -ForegroundColor Yellow
    Write-Host "  Add-MpExclusion -Path 'C:\Windows\System32\WindowsPowerShell'" -ForegroundColor Cyan
} else {
    Write-Host "  [OK] Startup time is acceptable!" -ForegroundColor Green
}

# Optional: Clean up old profile backups
Write-Host ""
Write-Host "[CLEANUP] Removing old profile backups..." -ForegroundColor Yellow
$backupDir = "C:\Users\N-Xyme\Documents\PowerShell"
Get-ChildItem $backupDir -Filter "*.ps1.bak" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  Removing: $($_.Name)" -ForegroundColor Gray
    Remove-Item $_.FullName -Force
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Done! Restart your terminal to test." -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
