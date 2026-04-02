# Enable Windows Voice Access
# Run as Administrator

Write-Host "Enabling Voice Access..." -ForegroundColor Cyan

# Enable Voice Access via registry
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\VoiceAccess"
if (-not (Test-Path $regPath)) {
    New-Item -Path $regPath -Force | Out-Null
}
Set-ItemProperty -Path $regPath -Name "Enabled" -Value 1 -Type DWord

# Enable Speech Recognition
$speechPath = "HKCU:\Software\Microsoft\Speech"
if (-not (Test-Path $speechPath)) {
    New-Item -Path $speechPath -Force | Out-Null
}

# Ensure Windows Speech Platform is installed
Write-Host "Checking Speech capabilities..." -ForegroundColor Yellow
Get-WindowsCapability -Online | Where-Object { $_.Name -like "*Speech*" } | ForEach-Object {
    if ($_.State -ne "Installed") {
        Write-Host "Installing: $($_.Name)" -ForegroundColor Green
        Add-WindowsCapability -Online -Name $_.Name
    } else {
        Write-Host "Already installed: $($_.Name)" -ForegroundColor Gray
    }
}

# Start Voice Access process
Write-Host "Starting Voice Access..." -ForegroundColor Green
Start-Process "ms-settings:easeofaccess-speech"

Write-Host "`nDone! Use Win+Ctrl+O to toggle Voice Access" -ForegroundColor Cyan
