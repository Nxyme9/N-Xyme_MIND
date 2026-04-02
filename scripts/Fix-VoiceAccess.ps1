# Voice Access Emergency Fix - Run as Administrator
Write-Host "=== VOICE ACCESS EMERGENCY FIX ===" -ForegroundColor Red

# 1. Kill zombie processes
Write-Host "[1/6] Killing speech processes..." -ForegroundColor Yellow
"VoiceAccess","SpeechRuntime","SpeechUXWorker","SpeechUX" | ForEach-Object {
    Stop-Process -Name $_ -Force -ErrorAction SilentlyContinue
}
Start-Sleep 2

# 2. Restart all related services
Write-Host "[2/6] Restarting services..." -ForegroundColor Yellow
@("AgentActivationRuntime*","hidserv","AudioSrv","AudioEndpointBuilder") | ForEach-Object {
    Get-Service -Name $_ -EA SilentlyContinue | ForEach-Object {
        $_ | Set-Service -StartupType Automatic -EA SilentlyContinue
        $_ | Restart-Service -Force -EA SilentlyContinue
        Write-Host "      $($_.Name): restarted" -ForegroundColor Green
    }
}

# 3. Re-register Voice Access app
Write-Host "[3/6] Re-registering Voice Access..." -ForegroundColor Yellow
Get-AppxPackage -AllUsers | Where-Object { $_.Name -match "VoiceAccess|NUIVoice" } | ForEach-Object {
    $m = Join-Path $_.InstallLocation "AppXManifest.xml"
    if (Test-Path $m) {
        Add-AppxPackage -Register $m -DisableDevelopmentMode -EA SilentlyContinue
        Write-Host "      $($_.Name): re-registered" -ForegroundColor Green
    }
}

# 4. Reset microphone privacy
Write-Host "[4/6] Resetting mic permissions..." -ForegroundColor Yellow
$mic = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
Set-ItemProperty -Path $mic -Name "Value" -Value "Allow" -Force
$speech = "HKCU:\Software\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy"
New-Item -Path $speech -Force | Out-Null
Set-ItemProperty -Path $speech -Name "HasAccepted" -Value 1 -Type DWord -Force
Write-Host "      Mic + online speech: ENABLED" -ForegroundColor Green

# 5. Disable USB selective suspend (kills USB mics)
Write-Host "[5/6] Disabling USB suspend..." -ForegroundColor Yellow
$scheme = (powercfg /getactivescheme).Split(':')[1].Trim().Split()[0]
powercfg /setacvalueindex $scheme 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0 | Out-Null

# 6. Launch settings
Write-Host "[6/6] Opening settings..." -ForegroundColor Yellow
Start-Process "ms-settings:easeofaccess-speech"

Write-Host "`n=== DONE ===" -ForegroundColor Cyan
Write-Host "Toggle Voice Access OFF then ON in the settings window" -ForegroundColor Yellow
