$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut("$env:USERPROFILE\Desktop\Voice Access.lnk")
$lnk.TargetPath = "C:\Windows\WinSxS\amd64_microsoft-windows-voiceaccessstub_31bf3856ad364e35_10.0.26100.8036_none_12ce8d2108862751\VoiceAccess.exe"
$lnk.Save()
Write-Host "Desktop shortcut created!" -ForegroundColor Green
