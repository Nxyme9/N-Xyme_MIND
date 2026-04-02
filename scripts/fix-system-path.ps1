# Fix System PATH Duplicates (Run as Admin)
# Removes duplicate entries from the system PATH environment variable

# Check admin
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell -> Run as Administrator" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "Fixing System PATH..." -ForegroundColor Cyan

# Read current system PATH
$currentPath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
$entries = $currentPath -split ';' | Where-Object { $_.Trim() -ne '' }

Write-Host "Current entries: $($entries.Count)"

# Remove duplicates (case-insensitive)
$seen = @{}
$unique = @()
foreach ($entry in $entries) {
    $key = $entry.Trim().TrimEnd('\').ToLower()
    if (-not $seen.ContainsKey($key)) {
        $seen[$key] = $true
        $unique += $entry.Trim()
    } else {
        Write-Host "  Removed duplicate: $entry" -ForegroundColor Yellow
    }
}

# Also remove trailing backslashes and normalize
$cleaned = $unique | ForEach-Object { $_.TrimEnd('\') }

# Write back
$newPath = $cleaned -join ';'
[Environment]::SetEnvironmentVariable('Path', $newPath, 'Machine')

Write-Host "`nSystem PATH fixed!" -ForegroundColor Green
Write-Host "  Before: $($entries.Count) entries" -ForegroundColor Gray
Write-Host "  After:  $($cleaned.Count) entries" -ForegroundColor Gray
Write-Host "`nRestart your terminal for changes to take effect." -ForegroundColor Yellow
