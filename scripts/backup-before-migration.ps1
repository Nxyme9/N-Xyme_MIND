# N-Xyme MIND Migration Backup Script
# Creates a timestamped backup of all critical data before migration

$ErrorActionPreference = "Stop"

# Configuration
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupRoot = "D:\01_CODING\backups\nxyme-catalyst-pre-migration"
$backupDir = Join-Path $backupRoot "backup_$timestamp"
$sourceRoot = "D:\01_CODING\00_N-Xyme_CATALYST"

# Colors for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) { Write-Output $args }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success { Write-ColorOutput Green $args }
function Write-Warning { Write-ColorOutput Yellow $args }
function Write-Error { Write-ColorOutput Red $args }
function Write-Info { Write-ColorOutput Cyan $args }

# Create backup directory
Write-Info "`n=== N-Xyme CATALYST Pre-Migration Backup ===`n"
Write-Info "Creating backup directory: $backupDir"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# Backup manifest
$manifest = @{
    timestamp = $timestamp
    source = $sourceRoot
    destination = $backupDir
    items = @()
}

function Backup-Directory {
    param(
        [string]$SourcePath,
        [string]$Description,
        [string]$RelativePath
    )
    
    $destPath = Join-Path $backupDir $RelativePath
    
    if (Test-Path $SourcePath) {
        Write-Info "Backing up: $Description"
        try {
            $destDir = Split-Path $destPath -Parent
            if (-not (Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            Copy-Item -Path $SourcePath -Destination $destPath -Recurse -Force
            Write-Success "  ✓ Completed"
            $script:manifest.items += @{
                type = "directory"
                description = $Description
                source = $SourcePath
                destination = $destPath
                status = "success"
            }
        }
        catch {
            Write-Error "  ✗ Failed: $_"
            $script:manifest.items += @{
                type = "directory"
                description = $Description
                source = $SourcePath
                destination = $destPath
                status = "failed"
                error = $_.Exception.Message
            }
        }
    }
    else {
        Write-Warning "  ⚠ Not found: $SourcePath"
        $script:manifest.items += @{
            type = "directory"
            description = $Description
            source = $SourcePath
            status = "not_found"
        }
    }
}

function Backup-File {
    param(
        [string]$SourcePath,
        [string]$Description,
        [string]$RelativePath
    )
    
    $destPath = Join-Path $backupDir $RelativePath
    
    if (Test-Path $SourcePath) {
        Write-Info "Backing up: $Description"
        try {
            $destDir = Split-Path $destPath -Parent
            if (-not (Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            Copy-Item -Path $SourcePath -Destination $destPath -Force
            Write-Success "  ✓ Completed"
            $script:manifest.items += @{
                type = "file"
                description = $Description
                source = $SourcePath
                destination = $destPath
                status = "success"
            }
        }
        catch {
            Write-Error "  ✗ Failed: $_"
            $script:manifest.items += @{
                type = "file"
                description = $Description
                source = $SourcePath
                destination = $destPath
                status = "failed"
                error = $_.Exception.Message
            }
        }
    }
    else {
        Write-Warning "  ⚠ Not found: $SourcePath"
        $script:manifest.items += @{
            type = "file"
            description = $Description
            source = $SourcePath
            status = "not_found"
        }
    }
}

# ============================================
# BACKUP SECTIONS
# ============================================

Write-Info "`n--- Core Jarvis System ---"
Backup-Directory "$sourceRoot\jarvis\engine" "Jarvis Engine (Voice, Vision, Brain)" "jarvis\engine"
Backup-Directory "$sourceRoot\jarvis\agent" "Jarvis Agent (Loop, Tools, Memory)" "jarvis\agent"
Backup-Directory "$sourceRoot\jarvis\skills" "Jarvis Skills (Browser, Desktop)" "jarvis\skills"
Backup-Directory "$sourceRoot\jarvis\adhd" "ADHD Features (Focus, Tracking)" "jarvis\adhd"
Backup-Directory "$sourceRoot\jarvis\ui" "UI Components (Hub, Palette)" "jarvis\ui"
Backup-Directory "$sourceRoot\jarvis\api" "API Server (FastAPI, PWA)" "jarvis\api"
Backup-File "$sourceRoot\jarvis\main.py" "Jarvis Main Entry Point" "jarvis\main.py"
Backup-File "$sourceRoot\jarvis\__init__.py" "Jarvis Package Init" "jarvis\__init__.py"

Write-Info "`n--- Configuration ---"
Backup-Directory "$sourceRoot\configs\jarvis" "Jarvis Configs" "configs\jarvis"
Backup-Directory "$sourceRoot\configs\opencode" "OpenCode Configs" "configs\opencode"
Backup-Directory "$sourceRoot\configs\agents" "Agent Definitions" "configs\agents"
Backup-Directory "$sourceRoot\configs\graphiti" "Graphiti Configs" "configs\graphiti"
Backup-Directory "$sourceRoot\configs\ollama" "Ollama Configs" "configs\ollama"
Backup-File "$sourceRoot\configs\app_config.py" "App Configuration" "configs\app_config.py"
Backup-File "$sourceRoot\configs\ports.md" "Port Assignments" "configs\ports.md"

Write-Info "`n--- Scripts ---"
Backup-File "$sourceRoot\scripts\start-nxyme-mind.py" "MIND Startup Script" "scripts\start-nxyme-mind.py"
Backup-File "$sourceRoot\scripts\start-nxyme-mind.bat" "MIND Startup Batch" "scripts\start-nxyme-mind.bat"

Write-Info "`n--- Memory System ---"
Backup-Directory "$sourceRoot\memory" "Memory System" "memory"

Write-Info "`n--- Data (Runtime) ---"
Backup-File "$sourceRoot\data\jarvis_events.db" "Jarvis Events DB" "data\jarvis_events.db"
Backup-File "$sourceRoot\data\jarvis_memory.db" "Jarvis Memory DB" "data\jarvis_memory.db"
Backup-File "$sourceRoot\data\jarvis_scheduler.db" "Jarvis Scheduler DB" "data\jarvis_scheduler.db"
Backup-File "$sourceRoot\data\nxyme.db" "N-Xyme DB" "data\nxyme.db"
Backup-File "$sourceRoot\data\audio_config.json" "Audio Configuration" "data\audio_config.json"
Backup-Directory "$sourceRoot\data\neo4j" "Neo4j Data" "data\neo4j"

Write-Info "`n--- Sisyphus Rules & Plans ---"
Backup-Directory "$sourceRoot\.sisyphus\rules" "Sisyphus Rules" ".sisyphus\rules"
Backup-Directory "$sourceRoot\.sisyphus\plans" "Sisyphus Plans" ".sisyphus\plans"
Backup-File "$sourceRoot\.sisyphus\session-config.json" "Session Config" ".sisyphus\session-config.json"
Backup-File "$sourceRoot\.sisyphus\boulder.json" "Boulder Config" ".sisyphus\boulder.json"

Write-Info "`n--- Environment & Config Files ---"
Backup-File "$sourceRoot\.env.example" "Environment Example" ".env.example"
Backup-File "$sourceRoot\docker-compose.yml" "Docker Compose" "docker-compose.yml"
Backup-File "$sourceRoot\docker-compose.override.yml" "Docker Compose Override" "docker-compose.override.yml"
Backup-File "$sourceRoot\package.json" "Package.json" "package.json"
Backup-File "$sourceRoot\pyproject.toml" "Python Project Config" "pyproject.toml"
Backup-File "$sourceRoot\requirements.txt" "Python Requirements" "requirements.txt"

# ============================================
# SAVE MANIFEST
# ============================================

Write-Info "`n--- Saving Backup Manifest ---"
$manifestPath = Join-Path $backupDir "backup-manifest.json"
$manifest | ConvertTo-Json -Depth 10 | Out-File -FilePath $manifestPath -Encoding UTF8
Write-Success "Manifest saved: $manifestPath"

# ============================================
# SUMMARY
# ============================================

$successCount = ($manifest.items | Where-Object { $_.status -eq "success" }).Count
$failedCount = ($manifest.items | Where-Object { $_.status -eq "failed" }).Count
$notFoundCount = ($manifest.items | Where-Object { $_.status -eq "not_found" }).Count

Write-Info "`n=== Backup Summary ==="
Write-Success "✓ Successful: $successCount"
if ($failedCount -gt 0) {
    Write-Error "✗ Failed: $failedCount"
}
if ($notFoundCount -gt 0) {
    Write-Warning "⚠ Not Found: $notFoundCount"
}

Write-Info "`nBackup location: $backupDir"
Write-Info "Total items backed up: $($manifest.items.Count)"

# Create a compressed archive
Write-Info "`nCreating compressed archive..."
$archivePath = "$backupRoot\backup_$timestamp.zip"
try {
    Compress-Archive -Path $backupDir -DestinationPath $archivePath -CompressionLevel Optimal
    Write-Success "Archive created: $archivePath"
    
    # Calculate sizes
    $backupSize = (Get-ChildItem -Path $backupDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    $archiveSize = (Get-Item $archivePath).Length / 1MB
    Write-Info "Backup size: $([math]::Round($backupSize, 2)) MB"
    Write-Info "Archive size: $([math]::Round($archiveSize, 2)) MB"
}
catch {
    Write-Warning "Could not create archive: $_"
}

Write-Info "`n=== Backup Complete ===`n"
