# Re-register speech components
Write-Host "Re-registering speech components..." -ForegroundColor Yellow

# Re-register SAPI
regsvr32 /s "C:\Windows\System32\Speech\Common\sapi.dll"
Write-Host "[1] SAPI registered" -ForegroundColor Green

# Start SpeechRuntime service if not running
$speechSvc = Get-Service SpeechRuntime -EA SilentlyContinue
if ($speechSvc) {
    if ($speechSvc.Status -ne "Running") {
        Start-Service SpeechRuntime -EA SilentlyContinue
        Write-Host "[2] SpeechRuntime started" -ForegroundColor Green
    } else {
        Write-Host "[2] SpeechRuntime already running" -ForegroundColor Green
    }
} else {
    Write-Host "[2] SpeechRuntime service not found!" -ForegroundColor Red
}

# Restart TextInputHost
Stop-Process TextInputHost -Force -EA SilentlyContinue
Start-Sleep 2
Write-Host "[3] TextInputHost restarted" -ForegroundColor Green

# Test if dictation works now
Write-Host ""
Write-Host "=== TEST NOW ===" -ForegroundColor Cyan
Write-Host "1. Open Notepad or any text field" -ForegroundColor White
Write-Host "2. Press Win+H" -ForegroundColor White
Write-Host "3. You should see a dictation bar" -ForegroundColor White
