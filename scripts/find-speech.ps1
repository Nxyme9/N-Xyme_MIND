Write-Host "=== ALL SPEECH SERVICES ===" -ForegroundColor Cyan
Get-Service | Where-Object { $_.Name -match "Speech" -or $_.DisplayName -match "Speech" } | Format-Table Name, DisplayName, Status, StartType

Write-Host "`n=== CHECKING SPEECHRUNTIME.EXE ===" -ForegroundColor Cyan
if (Test-Path "C:\Windows\System32\SpeechRuntime.exe") {
    Write-Host "SpeechRuntime.exe EXISTS" -ForegroundColor Green
    Get-Item "C:\Windows\System32\SpeechRuntime.exe" | Select-Object FullName, Length
} else {
    Write-Host "SpeechRuntime.exe NOT FOUND!" -ForegroundColor Red
}

Write-Host "`n=== TEXTINPUTHOST STATUS ===" -ForegroundColor Cyan
Get-Process TextInputHost -EA SilentlyContinue | Select-Object Id, ProcessName, CPU
