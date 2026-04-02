# Quick Voice Access Reset - Run as Admin
Write-Host "Resetting Voice Access..." -ForegroundColor Cyan

# 1. Kill stuck process
Stop-Process -Name 'VoiceAccess' -Force -ErrorAction SilentlyContinue
Write-Host "[1/4] Killed stuck process" -ForegroundColor Green

# 2. Restart speech service
Restart-Service -Name 'SpeechRuntime' -Force -ErrorAction SilentlyContinue
Write-Host "[2/4] Restarted SpeechRuntime" -ForegroundColor Green

# 3. Clear corrupted profile
Remove-Item "$env:LOCALAPPDATA\Speech\VoiceAccess" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "[3/4] Cleared profile cache" -ForegroundColor Green

# 4. Re-register Voice Access app
Get-AppxPackage *VoiceAccess* | Reset-AppxPackage -ErrorAction SilentlyContinue
Write-Host "[4/4] Reset Voice Access app" -ForegroundColor Green

Write-Host "`nDone! Try Win+H now (hold to dictate)" -ForegroundColor Cyan
Write-Host "Or open Settings > Accessibility > Speech > Voice Access" -ForegroundColor Yellow
