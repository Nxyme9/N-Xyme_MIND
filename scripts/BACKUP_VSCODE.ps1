# ============================================================
# VS CODE & EXTENSIONS BACKUP
# Saves: Extensions, Settings, Keybindings, Snippets, Profiles
# ============================================================

$BackupDir = "D:\N-Xyme_PRE_WIN11_UPGRADE\VSCODE_BACKUP"
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$codeDir = "C:\Users\N-Xyme\.vscode"
$extensionsBackup = "$BackupDir\extensions.txt"
$settingsBackup = "$BackupDir\settings.json"
$keybindingsBackup = "$BackupDir\keybindings.json"
$snippetsBackup = "$BackupDir\snippets"
$profilesBackup = "$BackupDir\profiles"

Write-Host "Backing up VS Code..."

# 1. Extensions List
Write-Host "  [1/5] Exporting extensions list..."
code --list-extensions > "$extensionsBackup"

# 2. Settings
Write-Host "  [2/5] Copying settings..."
if (Test-Path "$codeDir\settings.json") {
    Copy-Item "$codeDir\settings.json" "$settingsBackup"
}
if (Test-Path "$codeDir\settings.json.code-workspace") {
    Copy-Item "$codeDir\settings.json.code-workspace" "$BackupDir\settings.json.code-workspace"
}

# 3. Keybindings
Write-Host "  [3/5] Copying keybindings..."
if (Test-Path "$codeDir\keybindings.json") {
    Copy-Item "$codeDir\keybindings.json" "$keybindingsBackup"
}

# 4. Snippets
Write-Host "  [4/5] Copying snippets..."
if (Test-Path "$codeDir\snippets") {
    Copy-Item "$codeDir\snippets" "$snippetsBackup" -Recurse -Force
}

# 5. Profiles
Write-Host "  [5/5] Copying profiles..."
if (Test-Path "$codeDir\profiles") {
    Copy-Item "$codeDir\profiles" "$profilesBackup" -Recurse -Force
}

# 6. Extensions folder (for offline restore)
$extensionsFolderBackup = "$BackupDir\extensions_full"
Write-Host "  [6/6] Copying extensions folder..."
if (Test-Path "$env:USERPROFILE\.vscode\extensions") {
    Copy-Item "$env:USERPROFILE\.vscode\extensions" "$extensionsFolderBackup" -Recurse -Force -Exclude ".obsolete"
}

$extCount = (Get-Content "$extensionsBackup").Count
Write-Host ""
Write-Host "✅ VS Code backup complete!"
Write-Host "   Extensions: $extCount"
Write-Host "   Location: $BackupDir"
Write-Host ""
Write-Host "RESTORE AFTER WIN11:"
Write-Host "  1. Install VS Code"
Write-Host "  2. code --install-extension < ext1"
Write-Host "  3. code --install-extension < ext2..."
Write-Host "  OR: Copy back entire .vscode folder"
