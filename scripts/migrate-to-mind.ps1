# N-Xyme MIND Migration Script
# Copies optimized code from CATALYST to new MIND repository

$ErrorActionPreference = "Stop"

# Configuration
$sourceRoot = "D:\01_CODING\00_N-Xyme_CATALYST"
$targetRoot = "D:\01_CODING\00_N-Xyme_MIND"

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

# Migration manifest
$manifest = @{
    timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    source = $sourceRoot
    target = $targetRoot
    items = @()
}

function Copy-Directory {
    param(
        [string]$SourcePath,
        [string]$TargetPath,
        [string]$Description
    )
    
    if (Test-Path $SourcePath) {
        Write-Info "Copying: $Description"
        try {
            $targetDir = Split-Path $TargetPath -Parent
            if (-not (Test-Path $targetDir)) {
                New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
            }
            Copy-Item -Path $SourcePath -Destination $TargetPath -Recurse -Force
            Write-Success "  ✓ Completed"
            $script:manifest.items += @{
                type = "directory"
                description = $Description
                source = $SourcePath
                target = $TargetPath
                status = "success"
            }
        }
        catch {
            Write-Error "  ✗ Failed: $_"
            $script:manifest.items += @{
                type = "directory"
                description = $Description
                source = $SourcePath
                target = $TargetPath
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

function Copy-File {
    param(
        [string]$SourcePath,
        [string]$TargetPath,
        [string]$Description
    )
    
    if (Test-Path $SourcePath) {
        Write-Info "Copying: $Description"
        try {
            $targetDir = Split-Path $TargetPath -Parent
            if (-not (Test-Path $targetDir)) {
                New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
            }
            Copy-Item -Path $SourcePath -Destination $TargetPath -Force
            Write-Success "  ✓ Completed"
            $script:manifest.items += @{
                type = "file"
                description = $Description
                source = $SourcePath
                target = $TargetPath
                status = "success"
            }
        }
        catch {
            Write-Error "  ✗ Failed: $_"
            $script:manifest.items += @{
                type = "file"
                description = $Description
                source = $SourcePath
                target = $TargetPath
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
# PRE-FLIGHT CHECKS
# ============================================

Write-Info "`n=== N-Xyme MIND Migration ===`n"

# Check if source exists
if (-not (Test-Path $sourceRoot)) {
    Write-Error "Source directory not found: $sourceRoot"
    exit 1
}

# Check if target already exists
if (Test-Path $targetRoot) {
    Write-Warning "Target directory already exists: $targetRoot"
    $response = Read-Host "Do you want to continue and overwrite? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Info "Migration cancelled."
        exit 0
    }
}

# Check if backup exists
$backupRoot = "D:\01_CODING\backups\nxyme-catalyst-pre-migration"
if (-not (Test-Path $backupRoot)) {
    Write-Warning "No backup found at $backupRoot"
    $response = Read-Host "Have you run the backup script? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Info "Please run backup-before-migration.ps1 first."
        exit 1
    }
}

# Create target directory
Write-Info "Creating target directory: $targetRoot"
New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null

# ============================================
# COPY CORE JARVIS SYSTEM
# ============================================

Write-Info "`n--- Core Jarvis System ---"
Copy-Directory "$sourceRoot\jarvis\engine" "$targetRoot\jarvis\engine" "Jarvis Engine (Voice, Vision, Brain)"
Copy-Directory "$sourceRoot\jarvis\agent" "$targetRoot\jarvis\agent" "Jarvis Agent (Loop, Tools, Memory)"
Copy-Directory "$sourceRoot\jarvis\skills" "$targetRoot\jarvis\skills" "Jarvis Skills (Browser, Desktop)"
Copy-Directory "$sourceRoot\jarvis\adhd" "$targetRoot\jarvis\adhd" "ADHD Features (Focus, Tracking)"
Copy-Directory "$sourceRoot\jarvis\ui" "$targetRoot\jarvis\ui" "UI Components (Hub, Palette)"
Copy-Directory "$sourceRoot\jarvis\api" "$targetRoot\jarvis\api" "API Server (FastAPI, PWA)"
Copy-File "$sourceRoot\jarvis\main.py" "$targetRoot\jarvis\main.py" "Jarvis Main Entry Point"
Copy-File "$sourceRoot\jarvis\__init__.py" "$targetRoot\jarvis\__init__.py" "Jarvis Package Init"

# ============================================
# COPY CONFIGURATION
# ============================================

Write-Info "`n--- Configuration ---"
Copy-Directory "$sourceRoot\configs\jarvis" "$targetRoot\configs\jarvis" "Jarvis Configs"
Copy-Directory "$sourceRoot\configs\opencode" "$targetRoot\configs\opencode" "OpenCode Configs"
Copy-Directory "$sourceRoot\configs\agents" "$targetRoot\configs\agents" "Agent Definitions"
Copy-Directory "$sourceRoot\configs\graphiti" "$targetRoot\configs\graphiti" "Graphiti Configs"
Copy-Directory "$sourceRoot\configs\ollama" "$targetRoot\configs\ollama" "Ollama Configs"
Copy-File "$sourceRoot\configs\app_config.py" "$targetRoot\configs\app_config.py" "App Configuration"
Copy-File "$sourceRoot\configs\ports.md" "$targetRoot\configs\ports.md" "Port Assignments"

# ============================================
# COPY SCRIPTS
# ============================================

Write-Info "`n--- Scripts ---"
Copy-File "$sourceRoot\scripts\start-nxyme-mind.py" "$targetRoot\scripts\start-mind.py" "MIND Startup Script"
Copy-File "$sourceRoot\scripts\start-nxyme-mind.bat" "$targetRoot\scripts\start-mind.bat" "MIND Startup Batch"

# ============================================
# COPY MEMORY SYSTEM
# ============================================

Write-Info "`n--- Memory System ---"
Copy-Directory "$sourceRoot\memory" "$targetRoot\memory" "Memory System"

# ============================================
# COPY RULES
# ============================================

Write-Info "`n--- Rules ---"
Copy-Directory "$sourceRoot\.sisyphus\rules" "$targetRoot\.sisyphus\rules" "Sisyphus Rules"
Copy-File "$sourceRoot\.sisyphus\session-config.json" "$targetRoot\.sisyphus\session-config.json" "Session Config"
Copy-File "$sourceRoot\.sisyphus\boulder.json" "$targetRoot\.sisyphus\boulder.json" "Boulder Config"

# ============================================
# COPY ENVIRONMENT FILES
# ============================================

Write-Info "`n--- Environment Files ---"
Copy-File "$sourceRoot\.env.example" "$targetRoot\.env.example" "Environment Example"
Copy-File "$sourceRoot\docker-compose.yml" "$targetRoot\docker-compose.yml" "Docker Compose"
Copy-File "$sourceRoot\docker-compose.override.yml" "$targetRoot\docker-compose.override.yml" "Docker Compose Override"
Copy-File "$sourceRoot\package.json" "$targetRoot\package.json" "Package.json"
Copy-File "$sourceRoot\pyproject.toml" "$targetRoot\pyproject.toml" "Python Project Config"
Copy-File "$sourceRoot\requirements.txt" "$targetRoot\requirements.txt" "Python Requirements"

# ============================================
# UPDATE PATHS (CATALYST → MIND)
# ============================================

Write-Info "`n--- Updating Paths ---"

# Find and replace CATALYST with MIND in key files
$filesToUpdate = @(
    "$targetRoot\scripts\start-mind.py",
    "$targetRoot\scripts\start-mind.bat",
    "$targetRoot\configs\jarvis\*.json",
    "$targetRoot\configs\opencode\*.json"
)

foreach ($filePattern in $filesToUpdate) {
    $files = Get-ChildItem -Path $filePattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        Write-Info "Updating paths in: $($file.Name)"
        try {
            $content = Get-Content -Path $file.FullName -Raw
            $content = $content -replace "CATALYST", "MIND"
            $content = $content -replace "nxyme-catalyst", "nxyme-mind"
            Set-Content -Path $file.FullName -Value $content -NoNewline
            Write-Success "  ✓ Updated"
        }
        catch {
            Write-Warning "  ⚠ Could not update: $_"
        }
    }
}

# ============================================
# CREATE MIGRATION MANIFEST
# ============================================

Write-Info "`n--- Saving Migration Manifest ---"
$manifestPath = Join-Path $targetRoot "migration-manifest.json"
$manifest | ConvertTo-Json -Depth 10 | Out-File -FilePath $manifestPath -Encoding UTF8
Write-Success "Manifest saved: $manifestPath"

# ============================================
# SUMMARY
# ============================================

$successCount = ($manifest.items | Where-Object { $_.status -eq "success" }).Count
$failedCount = ($manifest.items | Where-Object { $_.status -eq "failed" }).Count
$notFoundCount = ($manifest.items | Where-Object { $_.status -eq "not_found" }).Count

Write-Info "`n=== Migration Summary ==="
Write-Success "✓ Successful: $successCount"
if ($failedCount -gt 0) {
    Write-Error "✗ Failed: $failedCount"
}
if ($notFoundCount -gt 0) {
    Write-Warning "⚠ Not Found: $notFoundCount"
}

Write-Info "`nTarget directory: $targetRoot"
Write-Info "Total items migrated: $($manifest.items.Count)"

# ============================================
# NEXT STEPS
# ============================================

Write-Info "`n=== Next Steps ==="
Write-Info "1. Review the migrated code in $targetRoot"
Write-Info "2. Initialize git repository: cd $targetRoot && git init"
Write-Info "3. Apply critical fixes from the checklist"
Write-Info "4. Test the migrated system"
Write-Info "5. Create initial commit: git add . && git commit -m 'Initial commit: N-Xyme MIND'"

Write-Info "`n=== Migration Complete ===`n"
