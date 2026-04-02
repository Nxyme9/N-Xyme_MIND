Write-Host "=== VOICE ACCESS DIAGNOSTIC ===" -ForegroundColor Cyan

Write-Host "`n[1] Windows Version:" -ForegroundColor Yellow
[Environment]::OSVersion.Version
(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').DisplayVersion

Write-Host "`n[2] Speech Packs:" -ForegroundColor Yellow
Get-WindowsCapability -Online | Where-Object Name -like 'Language.Speech*' | Select-Object Name, State

Write-Host "`n[3] Voice Access App:" -ForegroundColor Yellow
Get-AppxPackage *VoiceAccess* | Select-Object Name, Version, Status

Write-Host "`n[4] Speech Service:" -ForegroundColor Yellow
Get-Service SpeechRuntime -EA SilentlyContinue | Select-Object Name, Status, StartType

Write-Host "`n[5] Microphone Devices:" -ForegroundColor Yellow
Get-PnpDevice -Class AudioEndpoint -Status OK | Where-Object FriendlyName -match 'mic|Microphone'

Write-Host "`n[6] Policy Blocks:" -ForegroundColor Yellow
Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Speech' -EA SilentlyContinue

Write-Host "`n[7] Registry Enabled:" -ForegroundColor Yellow
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\VoiceAccess' -EA SilentlyContinue

Write-Host "`n=== DIAGNOSTIC COMPLETE ===" -ForegroundColor Cyan
