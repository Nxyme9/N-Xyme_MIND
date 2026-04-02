Write-Host "=== FINDING SPEECHRUNTIME ===" -ForegroundColor Cyan

# Get full paths from WinSxS
$files = Get-ChildItem 'C:\Windows\WinSxS' -Filter 'SpeechRuntime*' -Recurse -EA SilentlyContinue
foreach ($f in $files) {
    Write-Host $f.FullName -ForegroundColor Green
}

Write-Host "`n=== COPY TO SYSTEM32 ===" -ForegroundColor Cyan

# Find the newest one
$latest = $files | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($latest) {
    Write-Host "Source: $($latest.FullName)"
    Write-Host "Size: $($latest.Length) bytes"
    
    # Try to copy to System32
    try {
        Copy-Item $latest.FullName "C:\Windows\System32\SpeechRuntime.exe" -Force -EA Stop
        Write-Host "Copied to System32!" -ForegroundColor Green
    } catch {
        Write-Host "Copy failed: $_" -ForegroundColor Red
        Write-Host "Need admin to copy to System32" -ForegroundColor Yellow
    }
}
