# N-Xyme Catalyst - Add to Windows Startup
# Run this script once to add autostart.bat to Windows Startup folder

$startupFolder = [Environment]::GetFolderPath("Startup")
$batchFile = "D:\01_CODING\00_N-Xyme_CATALYST\scripts\autostart.bat"
$shortcutPath = Join-Path $startupFolder "N-Xyme Catalyst.lnk"

# Create shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = $batchFile
$Shortcut.WorkingDirectory = "D:\01_CODING\00_N-Xyme_CATALYST"
$Shortcut.Description = "N-Xyme Catalyst Auto-Start"
$Shortcut.Save()

Write-Host "✓ Added N-Xyme Catalyst to Windows Startup" -ForegroundColor Green
Write-Host "  Shortcut: $shortcutPath" -ForegroundColor Gray
Write-Host ""
Write-Host "Services will auto-start on next boot." -ForegroundColor Yellow
