# Verify PowerShell syntax for all scripts
$scripts = @(
    "health-check.ps1",
    "POST_WIN11_RESTORE.ps1",
    "start-nxyme-master.ps1"
)

foreach ($script in $scripts) {
    $path = Join-Path $PSScriptRoot $script
    if (Test-Path $path) {
        $parseErrors = $null
        $tokens = $null
        $ast = [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$parseErrors)
        if ($parseErrors.Count -gt 0) {
            Write-Host "FAIL: $script ($($parseErrors.Count) errors)" -ForegroundColor Red
            $parseErrors | ForEach-Object { Write-Host "  $($_.Message)" -ForegroundColor Red }
        } else {
            Write-Host "OK: $script" -ForegroundColor Green
        }
    } else {
        Write-Host "NOT FOUND: $script" -ForegroundColor Yellow
    }
}
