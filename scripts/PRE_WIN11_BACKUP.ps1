# ============================================================
# N-XYME - MASTER PRE-WIN11 UPGRADE BACKUP
# Run BEFORE clicking Install on Windows setup
# Saves: EVERYTHING you need to restore
# ============================================================

param(
    [string]$BackupDrive = "D:",
    [switch]$WhatIf
)

$ErrorActionPreference = "SilentlyContinue"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupRoot = "$BackupDrive\N-Xyme_WIN11_BACKUP"
$BackupDir = "$BackupRoot\$Timestamp"
$LogFile = "$BackupDir\_log.txt"

# ============================================================
function Log {
    param([string]$Msg, [string]$Level = "INFO")
    $ts = Get-Date -Format "HH:mm:ss"
    $entry = "[$ts] $Msg"
    Write-Host $entry
    Add-Content -Path $LogFile -Value $entry -ErrorAction SilentlyContinue
}

function Copy-Folder {
    param([string]$Source, [string]$Dest, [string]$Desc = "")
    if (Test-Path $Source) {
        Log "  COPY: $Source → $Dest ($Desc)"
        if (-not $WhatIf) {
            New-Item -ItemType Directory -Path (Split-Path $Dest) -Force | Out-Null
            Copy-Item -Path $Source -Destination $Dest -Recurse -Force
        }
    }
}

function Export-Registry {
    param([string]$Key, [string]$OutputFile)
    if (Test-Path $Key) {
        reg export $Key $OutputFile /y 2>$null | Out-Null
        Log "  REG: $Key → $OutputFile"
    }
}

# ============================================================
# INIT
# ============================================================
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
Log "=============================================="
Log "N-XYME PRE-WIN11 BACKUP"
Log "Target: $BackupDir"
Log "=============================================="

# ============================================================
# SECTION 1: USER HOME - FULL BACKUP
# ============================================================
Log "--- Section 1: User Home (C:\Users\N-Xyme) ---"

$userHome = "C:\Users\N-Xyme"

# Standard user folders
$userFolders = @(
    "Documents",
    "Downloads",
    "Pictures",
    "Videos",
    "Music",
    "Desktop",
    "Favorites",
    "Contacts",
    "Links",
    "Searches"
)

foreach ($folder in $userFolders) {
    $src = "$userHome\$folder"
    if (Test-Path $src) {
        $dest = "$BackupDir\USER_HOME\$folder"
        Log "  Copying: $folder"
        if (-not $WhatIf) {
            Copy-Item -Path $src -Destination $dest -Recurse -Force
        }
    }
}

# Dot-config directories (ALL of them - critical for dev tools)
$dotConfigs = @(
    ".config",
    ".vscode",
    ".claude",
    ".continue",
    ".codex",
    ".afirma",
    ".agent-browser",
    ".agents",
    ".ollama",
    ".openclaw",
    ".serena",
    ".cagent",
    ".cargo",
    ".rustup",
    ".gradle",
    ".m2",
    ".nuget",
    ".bun",
    ".docker",
    ".ssh",
    ".gnupg",
    ".wakatime",
    ".rest-client",
    ".ruff_cache",
    ".skiko",
    ".dotnet",
    ".npm-global"
)

foreach ($cfg in $dotConfigs) {
    $src = "$userHome\$cfg"
    if (Test-Path $src) {
        $dest = "$BackupDir\USER_HOME\$cfg"
        Log "  Copying: $cfg"
        if (-not $WhatIf) {
            Copy-Item -Path $src -Destination $dest -Recurse -Force
        }
    }
}

# ============================================================
# SECTION 2: GIT + SSH CONFIG
# ============================================================
Log "--- Section 2: Git + SSH ---"

Copy-Item -Path "$userHome\.gitconfig" -Destination "$BackupDir\USER_HOME\.gitconfig" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "$userHome\.git-credentials" -Destination "$BackupDir\USER_HOME\.git-credentials" -Force -ErrorAction SilentlyContinue

# ============================================================
# SECTION 3: APPDATA (WHERE ALL APP STATE LIVES)
# ============================================================
Log "--- Section 3: AppData (Critical App State) ---"

$appData = @(
    "$userHome\AppData\Local\npm",
    "$userHome\AppData\Roaming\npm",
    "$userHome\AppData\Local\Docker",
    "$userHome\AppData\Roaming\Docker Desktop",
    "$userHome\AppData\Local\JetBrains",
    "$userHome\AppData\Roaming\JetBrains",
    "$userHome\AppData\Roaming\Ableton",
    "$userHome\AppData\Local\Ableton",
    "$userHome\AppData\Roaming\obs-studio",
    "$userHome\AppData\Local\OBS Studio",
    "$userHome\AppData\Roaming\Code",
    "$userHome\AppData\Local\Android",
    "$userHome\AppData\Local\Google\Chrome\User Data",
    "$userHome\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup",
    "$userHome\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine"
)

foreach ($path in $appData) {
    if (Test-Path $path) {
        $safeName = $path -replace "C:\\Users\\N-Xyme\\", "" -replace "\\", "_"
        $dest = "$BackupDir\APPDATA\$safeName"
        Log "  Copying: $safeName"
        if (-not $WhatIf) {
            Copy-Item -Path $path -Destination $dest -Recurse -Force
        }
    }
}

# ============================================================
# SECTION 4: ABLETON + VST PLUGINS
# ============================================================
Log "--- Section 4: Ableton + VST Plugins ---"

$abletonPaths = @(
    "$userHome\Documents\Ableton",
    "C:\ProgramData\Ableton",
    "C:\Program Files\Ableton"
)

foreach ($path in $abletonPaths) {
    if (Test-Path $path) {
        $safeName = $path -replace "[:\\]", "_"
        $dest = "$BackupDir\ABLETON\$safeName"
        Log "  Copying: $path"
        if (-not $WhatIf) {
            Copy-Item -Path $path -Destination $dest -Recurse -Force
        }
    }
}

# VST Plugin locations (ALL common paths)
$vstPaths = @(
    "C:\Program Files\VSTPlugins",
    "C:\Program Files\Common Files\VST3",
    "C:\Program Files\Steinberg",
    "C:\Program Files\Common Files\Steinberg",
    "C:\Program Files\Native Instruments",
    "C:\Program Files\Common Files\Native Instruments",
    "C:\Program Files (x86)\VSTPlugins",
    "C:\Program Files (x86)\Steinberg",
    "C:\Program Files\FL Studio\Plugins",
    "C:\Program Files\Reaper\Plugins",
    "C:\Program Files\Image-Line",
    "C:\ProgramData\PluginAlliance",
    "C:\ProgramData\UVI",
    "C:\ProgramData\iZotope",
    "C:\ProgramData\FabFilter",
    "C:\ProgramData\Serato",
    "C:\ProgramData\Waves",
    "C:\ProgramData\Waves Audio",
    "C:\Program Files\Serato",
    "C:\Program Files\Waves",
    "C:\Program Files\Waves Audio",
    "C:\Program Files (x86)\Serato",
    "$userHome\Documents\VSTPlugins",
    "$userHome\Documents\VST3",
    "$userHome\AppData\Local\VirtualStore\Program Files",
    "$userHome\AppData\Local\VirtualStore\Program Files (x86)"
)

# Save VST paths list for later reference
$vstPaths | Out-File "$BackupDir\ABLETON\_VST_PATHS_FOUND.txt" -Encoding UTF8

foreach ($path in $vstPaths) {
    if (Test-Path $path) {
        $safeName = $path -replace "[:\\]", "_"
        $dest = "$BackupDir\ABLETON\$safeName"
        Log "  Copying VST: $path"
        if (-not $WhatIf) {
            Copy-Item -Path $path -Destination $dest -Recurse -Force
        }
    }
}

# ============================================================
# SECTION 5: FOCUSRITE + AUDIO DRIVERS
# ============================================================
Log "--- Section 5: Audio Drivers + Focusrite ---"

$audioPaths = @(
    "C:\Program Files\Focusrite",
    "C:\Program Files (x86)\Focusrite",
    "C:\ProgramData\Focusrite",
    "$userHome\AppData\Local\Focusrite",
    "$userHome\AppData\Roaming\Focusrite",
    "C:\Program Files\ASIO4ALL v2",
    "C:\Program Files\Voicemeeter",
    "C:\Program Files\VB Audio",
    "C:\ProgramData\Voicemeeter",
    "C:\ProgramData\VB Audio"
)

foreach ($path in $audioPaths) {
    if (Test-Path $path) {
        $safeName = $path -replace "[:\\]", "_"
        $dest = "$BackupDir\AUDIO\$safeName"
        Log "  Copying audio: $path"
        if (-not $WhatIf) {
            Copy-Item -Path $path -Destination $dest -Recurse -Force
        }
    }
}

# ============================================================
# SECTION 6: REGISTRY EXPORT (USER - SAFE)
# ============================================================
Log "--- Section 6: Registry Exports ---"

$regDir = "$BackupDir\REGISTRY"
New-Item -ItemType Directory -Path $regDir -Force | Out-Null

# User startup + environment
Export-Registry "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" "$regDir\HKCU_Run.reg"
Export-Registry "HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce" "$regDir\HKCU_RunOnce.reg"
Export-Registry "HKCU\Environment" "$regDir\HKCU_Environment.reg"
Export-Registry "HKCU\Software\Classes" "$regDir\HKCU_Classes.reg"

# Ableton registry
Export-Registry "HKLM\SOFTWARE\Ableton" "$regDir\HKLM_Ableton.reg"

# VST plugin registry entries
Export-Registry "HKLM\SOFTWARE\VST" "$regDir\HKLM_VST.reg"
Export-Registry "HKLM\SOFTWARE\Steinberg" "$regDir\HKLM_Steinberg.reg"

# Drivers
Export-Registry "HKLM\SOFTWARE\Focusrite" "$regDir\HKLM_Focusrite.reg"
Export-Registry "HKLM\SOFTWARE\Waves" "$regDir\HKLM_Waves.reg"
Export-Registry "HKLM\SOFTWARE\Serato" "$regDir\HKLM_Serato.reg"
Export-Registry "HKLM\SOFTWARE\Native Instruments" "$regDir\HKLM_NativeInstruments.reg"
Export-Registry "HKLM\SOFTWARE\iZotope" "$regDir\HKLM_iZotope.reg"
Export-Registry "HKLM\SOFTWARE\FabFilter" "$regDir\HKLM_FabFilter.reg"
Export-Registry "HKLM\SOFTWARE\PluginAlliance" "$regDir\HKLM_PluginAlliance.reg"

# ============================================================
# SECTION 7: ENVIRONMENT VARIABLES
# ============================================================
Log "--- Section 7: Environment Variables ---"

$envDir = "$BackupDir\ENV_VARS"
New-Item -ItemType Directory -Path $envDir -Force | Out-Null

# User env vars
$userVars = [Environment]::GetEnvironmentVariables("User")
$userVars.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" } | Out-File "$envDir\user_vars.txt" -Encoding UTF8

# Machine env vars (read-only)
$machineVars = [Environment]::GetEnvironmentVariables("Machine")
$machineVars.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" } | Out-File "$envDir\machine_vars.txt" -Encoding UTF8

Log "  Environment variables exported"

# ============================================================
# SECTION 8: HOSTS FILE + FIREWALL
# ============================================================
Log "--- Section 8: Network Config ---"

Copy-Item -Path "C:\Windows\System32\drivers\etc\hosts" -Destination "$BackupDir\NETWORK\hosts_backup.txt" -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "$BackupDir\NETWORK" -Force | Out-Null
netsh advfirewall export "$BackupDir\NETWORK\firewall_rules.wfw" 2>$null | Out-Null
Log "  Network config saved"

# ============================================================
# SECTION 9: SCHEDULED TASKS
# ============================================================
Log "--- Section 9: Scheduled Tasks ---"

$taskDir = "$BackupDir\TASKS"
New-Item -ItemType Directory -Path $taskDir -Force | Out-Null

Get-ScheduledTask | Where-Object { $_.Settings.Enabled -and $_.State -ne "Disabled" } | ForEach-Object {
    $taskName = $_.TaskName -replace "[\\/:*`"?<>|]", "_"
    Export-ScheduledTask -TaskName $_.TaskName -TaskPath $_.TaskPath 2>$null | Out-File "$taskDir\$taskName.xml" -Encoding UTF8
}
Log "  Scheduled tasks exported"

# ============================================================
# SECTION 10: PACKAGE MANAGER INVENTORIES
# ============================================================
Log "--- Section 10: Package Manager Inventories ---"

$pkgDir = "$BackupDir\PACKAGES"
New-Item -ItemType Directory -Path $pkgDir -Force | Out-Null

# VS Code extensions
if (Get-Command code -ErrorAction SilentlyContinue) {
    code --list-extensions > "$pkgDir\vscode_extensions.txt"
    Log "  VS Code extensions: $(Get-Content "$pkgDir\vscode_extensions.txt").Count"
}

# npm global
if (Get-Command npm -ErrorAction SilentlyContinue) {
    npm list -g --depth=0 --json 2>$null | Out-File "$pkgDir\npm_global.json"
    Log "  npm packages exported"
}

# pip
if (Get-Command pip -ErrorAction SilentlyContinue) {
    pip freeze > "$pkgDir\pip_packages.txt" 2>$null
    Log "  pip packages exported"
}

# cargo
if (Get-Command cargo -ErrorAction SilentlyContinue) {
    cargo install --list > "$pkgDir\cargo_packages.txt" 2>$null
    Log "  cargo packages exported"
}

# dotnet
if (Get-Command dotnet -ErrorAction SilentlyContinue) {
    dotnet tool list -g > "$pkgDir\dotnet_tools.txt" 2>$null
    Log "  dotnet tools exported"
}

# winget
if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget list > "$pkgDir\winget_installed.txt" 2>$null
    Log "  winget packages exported"
}

# WSL
if (Get-Command wsl -ErrorAction SilentlyContinue) {
    wsl --list --verbose > "$pkgDir\wsl_distros.txt" 2>$null
    Log "  WSL distros exported"
}

# ============================================================
# SECTION 11: INSTALLED PROGRAMS LIST
# ============================================================
Log "--- Section 11: Installed Programs ---"

# Get-Package
Get-Package | Select-Object Name, Version, ProviderName | Sort-Object Name | Export-Csv "$BackupDir\_installed_programs.csv" -NoTypeInformation
Log "  Programs: $((Import-Csv "$BackupDir\_installed_programs.csv").Count) installed"

# ============================================================
# SECTION 12: DOCKER VOLUMES
# ============================================================
Log "--- Section 12: Docker Volumes ---"

$dockerDir = "$BackupDir\DOCKER"
New-Item -ItemType Directory -Path $dockerDir -Force | Out-Null

$volumes = docker volume ls --format "{{.Name}}" 2>$null
foreach ($vol in $volumes) {
    Log "  Backing up Docker volume: $vol"
    if (-not $WhatIf) {
        docker run --rm -v ${vol}:/volume -v "${dockerDir}:/backup" alpine tar czf "/backup/${vol}.tar.gz" -C /volume ./ 2>$null
    }
}

# ============================================================
# SECTION 13: MANIFEST
# ============================================================
Log "--- Section 13: Creating Manifest ---"

$manifest = @{
    BackupDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    ComputerName = $env:COMPUTERNAME
    OSVersion = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion" -ErrorAction SilentlyContinue).ProductName
    Username = $env:USERNAME
    Sections = @(
        "USER_HOME - Documents, Downloads, Pictures, Desktop, etc.",
        "APPDATA - Local, Roaming app state",
        "ABLETON - Projects, library, VST plugins",
        "AUDIO - Focusrite, drivers, etc.",
        "REGISTRY - HKCU + HKLM exports for all apps",
        "ENV_VARS - User + Machine variables",
        "NETWORK - hosts, firewall rules",
        "TASKS - Scheduled tasks",
        "PACKAGES - VS Code, npm, pip, cargo, dotnet, winget, WSL",
        "DOCKER - Volume backups",
        "_installed_programs.csv - Full program list"
    )
    DockerContainers = @(
        "neo4j:5 - localhost:7474,7687",
        "graphiti-mcp - localhost:8001",
        "security-agent - localhost:5002"
    )
    CriticalNotes = @(
        "A:\ollama\models is on SEPARATE DRIVE - NOT backed up",
        "D:\ data drive is SEPARATE - NOT backed up",
        "Macrium image IS your OS backup",
        "This script backs up C: USER DATA + CONFIGS + REGISTRY"
    )
}

$manifest | ConvertTo-Json -Depth 5 | Out-File "$BackupDir\_MANIFEST.json" -Encoding UTF8

# ============================================================
# FINAL SUMMARY
# ============================================================
Log ""
Log "=============================================="
Log "BACKUP COMPLETE"
Log "=============================================="
Log "Location: $BackupDir"
Log "Log: $LogFile"
Log ""
Log "NEXT STEPS:"
Log "  1. Verify: dir /s $BackupDir"
Log "  2. Copy to USB/external if possible"
Log "  3. Proceed with Windows 11 install"
Log "  4. After Win11 boots, run POST_WIN11_RESTORE.ps1"
Log "=============================================="
