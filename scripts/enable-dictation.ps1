# Enable Native Windows Dictation
Write-Host "Enabling native dictation..." -ForegroundColor Yellow

# Enable dictation
New-Item 'HKCU:\Software\Microsoft\Input\Settings' -Force | Out-Null
Set-ItemProperty 'HKCU:\Software\Microsoft\Input\Settings' 'IsDictationEnabled' -Value 1 -Type DWord -Force
Set-ItemProperty 'HKCU:\Software\Microsoft\Input\Settings' 'IsDictationHotkeyEnabled' -Value 1 -Type DWord -Force
Write-Host "[1] Dictation enabled" -ForegroundColor Green

# Enable online speech recognition
New-Item 'HKCU:\Software\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy' -Force | Out-Null
Set-ItemProperty 'HKCU:\Software\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy' 'HasAccepted' -Value 1 -Type DWord -Force
Write-Host "[2] Online speech enabled" -ForegroundColor Green

# Restart TextInputHost to pick up changes
Stop-Process -Name TextInputHost -Force -ErrorAction SilentlyContinue
Start-Sleep 2
# It auto-restarts
Write-Host "[3] TextInputHost restarted" -ForegroundColor Green

Write-Host ""
Write-Host "DONE - Press Win+H in any text field to dictate" -ForegroundColor Cyan
