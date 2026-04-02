Write-Host "=== SPEECH SERVICES ===" -ForegroundColor Cyan
Get-Service | Where-Object { $_.Name -match "Speech" } | Format-Table Name, Status, StartType -AutoSize

Write-Host "`n=== LANGUAGE PACK ===" -ForegroundColor Cyan
$lang = Get-WinUserLanguageList
$lang | ForEach-Object {
    Write-Host "Language: $($_.LanguageTag)"
    Write-Host "Handwriting support: $($_.Handwriting)"
    Write-Host "Speech support: $($_.SpokenLanguage)"
}

Write-Host "`n=== DICTATION REGISTRY ===" -ForegroundColor Cyan
Get-ItemProperty "HKCU:\Software\Microsoft\Input\Settings" -EA SilentlyContinue | Format-List

Write-Host "`n=== IS DICTATION AVAILABLE? ===" -ForegroundColor Cyan
# Check if Win+H is intercepted
$hotkey = Get-ItemProperty "HKCU:\Software\Microsoft\Input\Settings" -Name "IsDictationHotkeyEnabled" -EA SilentlyContinue
if ($hotkey.IsDictationHotkeyEnabled -eq 1) {
    Write-Host "Win+H hotkey: ENABLED" -ForegroundColor Green
} else {
    Write-Host "Win+H hotkey: DISABLED" -ForegroundColor Red
}
