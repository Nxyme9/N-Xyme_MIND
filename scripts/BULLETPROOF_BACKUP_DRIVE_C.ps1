# ============================================================
# N-Xyme CATALYST - COMPLETE DRIVE C BULLETPROOF BACKUP
# Windows 10 → Windows 11 Enterprise Upgrade Safety Net
# Run this BEFORE you click anything on the Windows setup screen
# ============================================================

param(
    [string]$BackupDrive = "D:",
    [switch]$SkipLargeFiles,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupRoot = "$BackupDrive\N-Xyme_PRE_WIN11_UPGRADE"
$BackupPath = "$BackupRoot\$Timestamp"
$LogFile = "$BackupRoot\backup_log_$Timestamp.txt"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "[$ts] [$Level] $Message"
    Write-Host $entry
    Add-Content -Path $LogFile -Value $entry
}

function Get-FolderSize {
    param([string]$Path)
    if (Test-Path $Path) {
        $bytes = (Get-ChildItem $Path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        return [math]::Round($bytes / 1GB, 2)
    }
    return 0
}

# ============================================================
# SECTION 1: Create Backup Directory
# ============================================================
Write-Log "=============================================="
Write-Log "N-XYME BULLETPROOF BACKUP - DRIVE C"
Write-Log "Target: $BackupPath"
Write-Log "=============================================="

if ($WhatIf) {
    Write-Log "[WHATIF] Would create: $BackupPath" -Level "WARN"
}

New-Item -ItemType Directory -Path $BackupPath -Force -ErrorAction SilentlyContinue | Out-Null
New-Item -ItemType Directory -Path $BackupRoot -Force -ErrorAction SilentlyContinue | Out-Null

# ============================================================
# SECTION 2: Stop All Running Services (Docker, etc.)
# ============================================================
Write-Log "--- Stopping running services ---"

$servicesToStop = @(
    "Docker Desktop",
    "Neo4j"
)

foreach ($svc in $servicesToStop) {
    $svcObj = Get-Service -DisplayName $svc -ErrorAction SilentlyContinue
    if ($svcObj -and $svcObj.Status -eq "Running") {
        Write-Log "Stopping: $($svcObj.DisplayName)"
        Stop-Service -InputObject $svcObj -Force -ErrorAction SilentlyContinue
    }
}

# Docker compose down
$composeFiles = @(
    (Join-Path $ProjectRoot "docker-compose.yml"),
    (Join-Path $ProjectRoot "docker-compose.override.yml")
)
$composeFileArgs = $composeFiles | Where-Object { Test-Path $_ } | ForEach-Object { "-f `"$_`"" }
if ($composeFileArgs) {
    Write-Log "Running: docker-compose down"
    $proc = Start-Process -FilePath "docker-compose" -ArgumentList "$composeFileArgs down" -NoNewWindow -Wait -PassThru -ErrorAction SilentlyContinue
}

# ============================================================
# SECTION 3: Backup User Home (C:\Users\N-Xyme)
# ============================================================
Write-Log "--- Backing up User Home Directory ---"
$userHome = "C:\Users\N-Xyme"

# What needs to be saved - HIGH PRIORITY
$criticalUserItems = @(
    "Documents",
    "Downloads",
    "Pictures",
    "Videos",
    "Music",
    "Desktop",
    "Favorites",
    "Contacts",
    "Links",
    "Searches",
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
    ".serena"
)

$userBackupPath = "$BackupPath\C_Users_N-Xyme"
New-Item -ItemType Directory -Path $userBackupPath -Force -ErrorAction SilentlyContinue | Out-Null

foreach ($item in $criticalUserItems) {
    $src = Join-Path $userHome $item
    if (Test-Path $src) {
        $size = Get-FolderSize $src
        Write-Log "  Copying: $item ($size GB)"
        if (-not $WhatIf) {
            $dest = Join-Path $userBackupPath $item
            Copy-Item -Path $src -Destination $dest -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

# ============================================================
# SECTION 4: Backup N-Xyme CATALYST Code & Configs
# ============================================================
Write-Log "--- Backing up N-Xyme CATALYST Project ---"

$catalystPaths = @(
    (Join-Path $ProjectRoot "00_N-Xyme_CATALYST"),
    (Join-Path $ProjectRoot "00_N-Xyme_CATALYST\configs"),
    (Join-Path $ProjectRoot "00_N-Xyme_CATALYST\data"),
    "D:\01_CODING\N-Xyme_FORGE_Documentation",
    "D:\01_CODING\NX-VIBE"
)

$catalystBackupPath = "$BackupPath\D_01_CODING"
New-Item -ItemType Directory -Path $catalystBackupPath -Force -ErrorAction SilentlyContinue | Out-Null

# Selective backup of CATALYST - skip node_modules and cache
$catalyst = (Join-Path $ProjectRoot "00_N-Xyme_CATALYST")
Write-Log "  Copying: 00_N-Xyme_CATALYST (selective - skipping node_modules)"

if (-not $WhatIf) {
    $catDest = Join-Path $catalystBackupPath "00_N-Xyme_CATALYST"
    New-Item -ItemType Directory -Path $catDest -Force | Out-Null
    
    # Copy everything EXCEPT node_modules, .git, __pycache__, etc.
    $exclude = @("node_modules", ".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".ru", "logs", ".zap")
    Get-ChildItem -Path $catalyst -Directory | Where-Object { $_.Name -notin $exclude } | ForEach-Object {
        Write-Log "    + $($_.Name)"
        Copy-Item -Path $_.FullName -Destination (Join-Path $catDest $_.Name) -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # Copy root config files
    Get-ChildItem -Path $catalyst -File | Where-Object { $_.Name -notin @("package-lock.json", "pnpm-lock.yaml") } | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $catDest -Force -ErrorAction SilentlyContinue
    }
}

# ============================================================
# SECTION 5: Backup AI Models (OLLAMA)
# ============================================================
Write-Log "--- Backing up Ollama Models ---"

$ollamaModels = "A:\ollama\models"
if (Test-Path $ollamaModels) {
    $size = Get-FolderSize $ollamaModels
    Write-Log "  Ollama models found: $size GB"
    Write-Log "  ⚠️  RECOMMENDATION: Copy manually if space allows"
    
    $modelBackupPath = "$BackupPath\A_ollama_models"
    New-Item -ItemType Directory -Path $modelBackupPath -Force -ErrorAction SilentlyContinue | Out-Null
    
    if (-not $SkipLargeFiles -and -not $WhatIf) {
        Write-Log "  Copying Ollama models (this may take a long time)..."
        Copy-Item -Path $ollamaModels -Destination $modelBackupPath -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        # Just copy manifests and metadata
        Get-ChildItem -Path $ollamaModels -File | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $modelBackupPath -Force -ErrorAction SilentlyContinue
        }
        Get-ChildItem -Path $ollamaModels -Directory | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $modelBackupPath -Recurse -Force -ErrorAction SilentlyContinue -Exclude "blobs" -Include "manifests"
        }
        Write-Log "  ⚠️  MODELS SKIPPED - You must manually copy A:\ollama\models"
    }
} else {
    Write-Log "  Ollama models not found at $ollamaModels"
}

# ============================================================
# SECTION 6: Backup Docker Volumes
# ============================================================
Write-Log "--- Backing up Docker Volumes ---"

$dockerBackupPath = "$BackupPath\Docker_Volumes"
New-Item -ItemType Directory -Path $dockerBackupPath -Force -ErrorAction SilentlyContinue | Out-Null

try {
    $volumes = docker volume ls --format "{{.Name}}" 2>$null
    foreach ($vol in $volumes) {
        if ($vol -match "nxyme|catalyst|local") {
            Write-Log "  Backing up volume: $vol"
            if (-not $WhatIf) {
                docker run --rm -v ${vol}:/volume -v "${dockerBackupPath}:/backup" alpine tar czf "/backup/${vol}.tar.gz" -C /volume ./ 2>$null
            }
        }
    }
} catch {
    Write-Log "  Docker not available or no volumes found" -Level "WARN"
}

# ============================================================
# SECTION 7: Backup System Registry Exports (User)
# ============================================================
Write-Log "--- Exporting User Registry Keys ---"

$regBackupPath = "$BackupPath\Registry_Exports"
New-Item -ItemType Directory -Path $regBackupPath -Force -ErrorAction SilentlyContinue | Out-Null

$userRegKeys = @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKCU:\Environment"
)

foreach ($key in $userRegKeys) {
    $keyName = $key -replace ":", "_" -replace "\\", "_" -replace ":", ""
    $regFile = "$regBackupPath\$keyName.reg"
    Write-Log "  Exporting: $key"
    if (-not $WhatIf) {
        reg export $key $regFile /y 2>$null
    }
}

# ============================================================
# SECTION 8: Backup Windows Startup & Scheduled Tasks
# ============================================================
Write-Log "--- Exporting Startup & Scheduled Task Configs ---"

$startupBackupPath = "$BackupPath\Startup_Config"
New-Item -ItemType Directory -Path $startupBackupPath -Force -ErrorAction SilentlyContinue | Out-Null

# Export scheduled tasks
if (-not $WhatIf) {
    Get-ScheduledTask | Where-Object { $_.Settings.Enabled } | ForEach-Object {
        $taskName = $_.TaskName -replace "[\\/:*`"?<>|]", "_"
        Export-ScheduledTask -TaskName $_.TaskName -TaskPath $_.TaskPath | Out-File "$startupBackupPath\$taskName.xml" -ErrorAction SilentlyContinue
    }
}

# ============================================================
# SECTION 9: Environment Variables Export
# ============================================================
Write-Log "--- Exporting Environment Variables ---"

$envBackupPath = "$BackupPath\Environment_Variables"
New-Item -ItemType Directory -Path $envBackupPath -Force -ErrorAction SilentlyContinue | Out-Null

$envBackup = @()
$envBackup += "# USER ENVIRONMENT VARIABLES"
$envBackup += "# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$envBackup += ""
$envBackup += "[Environment]::GetEnvironmentVariables('User') | ConvertTo-Json | Out-File '$envBackupPath\user_env.json'"
$envBackup += ""
$envBackup += "# MACHINE ENVIRONMENT VARIABLES (requires Admin)"
$envBackup += "[Environment]::GetEnvironmentVariables('Machine') | ConvertTo-Json | Out-File '$envBackupPath\machine_env.json'"

$envBackup += ""
$envBackup += "# ACTUAL VALUES:"
$envBackup += ""

foreach ($var in [Environment]::GetEnvironmentVariables('User').GetEnumerator()) {
    $envBackup += "$($var.Key)=$($var.Value)"
}

$envBackup | Out-File "$envBackupPath\environment_variables.txt" -Encoding UTF8

# ============================================================
# SECTION 10: Ollama Service Config
# ============================================================
Write-Log "--- Exporting Ollama Service Config ---"

$ollamaConfig = "C:\Users\N-Xyme\.ollama"
if (Test-Path $ollamaConfig) {
    $ollamaBackupPath = "$BackupPath\A_ollama_config"
    New-Item -ItemType Directory -Path $ollamaBackupPath -Force -ErrorAction SilentlyContinue | Out-Null
    Copy-Item -Path $ollamaConfig -Destination $ollamaBackupPath -Recurse -Force -ErrorAction SilentlyContinue
    Write-Log "  Ollama config backed up"
}

# ============================================================
# SECTION 11: Create Backup Manifest
# ============================================================
Write-Log "--- Creating Backup Manifest ---"

$manifest = @{
    BackupDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    ComputerName = $env:COMPUTERNAME
    OSVersion = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion").ProductName
    UpgradeTarget = "Windows 10 Developer → Windows 11 Enterprise"
    BackupDrive = $BackupDrive
    Contents = @{
        UserHome = "$BackupPath\C_Users_N-Xyme"
        CatalystProject = "$BackupPath\D_01_CODING\00_N-Xyme_CATALYST"
        OllamaModels = "MANUAL COPY REQUIRED - See A:\ollama\models"
        DockerVolumes = "$BackupPath\Docker_Volumes"
        RegistryExports = "$BackupPath\Registry_Exports"
        StartupConfig = "$BackupPath\Startup_Config"
        EnvironmentVars = "$BackupPath\Environment_Variables"
    }
    CriticalPaths = @(
        "C:\Users\N-Xyme\.config\opencode",
        "C:\Users\N-Xyme\.vscode",
        "C:\Users\N-Xyme\.claude",
        (Join-Path $ProjectRoot "00_N-Xyme_CATALYST"),
        "D:\01_CODING\N-Xyme_FORGE_Documentation",
        "D:\01_CODING\NX-VIBE",
        "A:\ollama\models"
    )
    DockerContainers = @{
        neo4j = "localhost:7474, localhost:7687"
        graphiti = "localhost:8001"
        security_agent = "localhost:5002"
    }
}

$manifest | ConvertTo-Json -Depth 10 | Out-File "$BackupPath\BACKUP_MANIFEST.json" -Encoding UTF8

# ============================================================
# SECTION 12: Calculate Total Size & Summary
# ============================================================
Write-Log "=============================================="
Write-Log "BACKUP COMPLETED"
Write-Log "=============================================="

$totalSize = Get-FolderSize $BackupPath
Write-Log "Backup Location: $BackupPath"
Write-Log "Total Size: $totalSize GB"
Write-Log "Log File: $LogFile"
Write-Log "Manifest: $BackupPath\BACKUP_MANIFEST.json"

# ============================================================
# POST-BACKUP CHECKLIST
# ============================================================
Write-Log ""
Write-Log "=============================================="
Write-Log "POST-BACKUP CHECKLIST - DO THESE NOW:"
Write-Log "=============================================="
Write-Log ""
Write-Log "☐ 1. VERIFY the backup folder exists: $BackupPath"
Write-Log "☐ 2. CHECK backup manifest: $BackupPath\BACKUP_MANIFEST.json"
Write-Log "☐ 3. COPY Ollama models MANUALLY: robocopy 'A:\ollama\models' '$BackupPath\A_ollama_models' /E /MT:8"
Write-Log "☐ 4. Verify key files are present:"
Write-Log "     - $BackupPath\C_Users_N-Xyme\.config\opencode\opencode.json"
Write-Log "     - $BackupPath\D_01_CODING\00_N-Xyme_CATALYST\docker-compose.yml"
Write-Log "     - $BackupPath\Environment_Variables\environment_variables.txt"
Write-Log "☐ 5. COPY this entire $BackupRoot folder to a SECOND external drive if possible"
Write-Log "☐ 6. Then proceed with Windows 11 installation"
Write-Log ""
Write-Log "RECOVERY AFTER UPGRADE:"
Write-Log "  1. Install Docker Desktop for Windows"
Write-Log "  2. Copy back C:\Users\N-Xyme\.config\opencode"
Write-Log "  3. Copy back D:\01_CODING\00_N-Xyme_CATALYST"
Write-Log "  4. Run: docker-compose up -d"
Write-Log "  5. Restore Ollama models to A:\ollama\models"

Write-Log ""
Write-Log "=============================================="
Write-Log "BACKUP SCRIPT FINISHED: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Log "=============================================="
