# Try to restore Speech by running from WinSxS
Write-Host "=== RESTORING SPEECH RUNTIME ===" -ForegroundColor Cyan

$exe = "C:\Windows\WinSxS\amd64_microsoft-onecore-s..chservice-component_31bf3856ad364e35_10.0.26100.7920_none_492aee8d3c0c810f\r\SpeechRuntime.exe"

# Check file
if (Test-Path $exe) {
    Write-Host "SpeechRuntime.exe found!" -ForegroundColor Green
    Write-Host "Size: $((Get-Item $exe).Length) bytes"
} else {
    Write-Host "NOT FOUND!" -ForegroundColor Red
    exit 1
}

# Try to run it directly
Write-Host "`nAttempting to start SpeechRuntime from WinSxS..." -ForegroundColor Yellow
try {
    Start-Process $exe -WindowStyle Hidden -EA Stop
    Write-Host "Started!" -ForegroundColor Green
} catch {
    Write-Host "Failed to start: $_" -ForegroundColor Red
}

# Check if it's running
Start-Sleep 3
$proc = Get-Process SpeechRuntime -EA SilentlyContinue
if ($proc) {
    Write-Host "`nSpeechRuntime is RUNNING! (PID: $($proc.Id))" -ForegroundColor Green
} else {
    Write-Host "`nSpeechRuntime not running. Trying alternative..." -ForegroundColor Yellow
    
    # Try to register as a service using sc (needs admin but might work)
    sc.exe create SpeechRuntime binPath= "$exe" start= demand 2>&1
    sc.exe start SpeechRuntime 2>&1
}

# Now test Win+H
Write-Host "`n=== TEST NOW ===" -ForegroundColor Cyan
Write-Host "1. Open Notepad" -ForegroundColor White
Write-Host "2. Press Win+H" -ForegroundColor White
Write-Host "3. Dictation bar should appear" -ForegroundColor White
