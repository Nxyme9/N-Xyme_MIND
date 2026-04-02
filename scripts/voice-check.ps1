Write-Host "=== DEEP CHECK ===" -ForegroundColor Cyan

Write-Host "`n[1] Voice Access App:" -ForegroundColor Yellow
Get-AppxPackage | Where-Object { $_.Name -match "VoiceAccess" } | Select-Object Name, Version, Status | Format-List

Write-Host "[2] SpeechRuntime Process:" -ForegroundColor Yellow
Get-Process SpeechRuntime -EA SilentlyContinue

Write-Host "[3] Microphone Devices:" -ForegroundColor Yellow
Get-PnpDevice -Class AudioEndpoint -Status OK | Where-Object { $_.FriendlyName -match "Mic" } | Select-Object FriendlyName, Status

Write-Host "[4] Audio Services:" -ForegroundColor Yellow
Get-Service -Name "hidserv","AudioSrv","AudioEndpointBuilder" | Select-Object Name, Status

Write-Host "[5] Windows Build:" -ForegroundColor Yellow
(Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion").DisplayVersion
