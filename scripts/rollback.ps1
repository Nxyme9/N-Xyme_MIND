# N-Xyme Catalyst Rollback Script
# Restores system to a previous backup state

param(
    [string]$BackupDir = "$PSScriptRoot\backups",
    [string]$TargetBackup,
    [switch]$ListBackups,
    [switch]$Force,
    [switch]$Help
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile = Join-Path $BackupDir "rollback.log"

# Function to log messages
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Write-Host $LogMessage
    Add-Content -Path $LogFile -Value $LogMessage
}

# Function to list available backups
function List-Backups {
    Write-Log "Listing available backups..."
    
    if (!(Test-Path $BackupDir)) {
        Write-Log "No backup directory found at $BackupDir" -Level "WARN"
        return
    }
    
    $Backups = Get-ChildItem -Path $BackupDir -Directory | Sort-Object CreationTime -Descending
    
    if ($Backups.Count -eq 0) {
        Write-Log "No backups found" -Level "WARN"
        return
    }
    
    Write-Host "`nAvailable Backups:"
    Write-Host "=================="
    
    foreach ($Backup in $Backups) {
        $ManifestPath = Join-Path $Backup.FullName "manifest.json"
        $Size = "{0:N2} MB" -f ((Get-ChildItem $Backup.FullName -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB)
        
        if (Test-Path $ManifestPath) {
            $Manifest = Get-Content $ManifestPath | ConvertFrom-Json
            Write-Host "  [$($Backup.CreationTime.ToString('yyyy-MM-dd HH:mm:ss'))] $($Backup.Name)"
            Write-Host "    Size: $Size"
            Write-Host "    Includes data: $($Manifest.includes_data)"
            Write-Host "    Path: $($Backup.FullName)"
        } else {
            Write-Host "  [$($Backup.CreationTime.ToString('yyyy-MM-dd HH:mm:ss'))] $($Backup.Name) (no manifest)"
            Write-Host "    Size: $Size"
            Write-Host "    Path: $($Backup.FullName)"
        }
        Write-Host ""
    }
}

# Function to validate backup
function Test-Backup {
    param([string]$BackupPath)
    
    if (!(Test-Path $BackupPath)) {
        Write-Log "Backup path does not exist: $BackupPath" -Level "ERROR"
        return $false
    }
    
    $ManifestPath = Join-Path $BackupPath "manifest.json"
    if (!(Test-Path $ManifestPath)) {
        Write-Log "Backup manifest not found" -Level "WARN"
    }
    
    # Check for critical directories
    $CriticalPaths = @(
        "configs",
        "docs"
    )
    
    foreach ($path in $CriticalPaths) {
        $FullPath = Join-Path $BackupPath $path
        if (!(Test-Path $FullPath)) {
            Write-Log "Warning: Missing directory $path in backup" -Level "WARN"
        }
    }
    
    return $true
}

# Function to restore configuration
function Restore-Configs {
    param([string]$BackupPath)
    
    Write-Log "Restoring configuration files..."
    
    $ConfigBackup = Join-Path $BackupPath "configs"
    if (Test-Path $ConfigBackup) {
        # Restore main config directories
        $TargetConfigs = Join-Path $ScriptDir "..\configs"
        
        # Backup current configs first
        $BackupTimestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
        $CurrentBackup = Join-Path $BackupDir "pre-restore-backup_$BackupTimestamp"
        New-Item -ItemType Directory -Path $CurrentBackup -Force | Out-Null
        
        if (Test-Path $TargetConfigs) {
            Copy-Item -Path "$TargetConfigs\*" -Destination $CurrentBackup -Recurse -Force
            Write-Log "Backed up current configs to $CurrentBackup"
        }
        
        # Restore from backup
        $ConfigsSource = Join-Path $ConfigBackup "configs"
        if (Test-Path $ConfigsSource) {
            Copy-Item -Path "$ConfigsSource\*" -Destination $TargetConfigs -Recurse -Force
            Write-Log "Restored configs from backup"
        }
        
        # Restore docs
        $DocsSource = Join-Path $ConfigBackup "docs"
        $TargetDocs = Join-Path $ScriptDir "..\docs"
        if (Test-Path $DocsSource) {
            Copy-Item -Path "$DocsSource\*" -Destination $TargetDocs -Recurse -Force
            Write-Log "Restored docs from backup"
        }
        
        # Restore root config files
        $RootFiles = Get-ChildItem $ConfigBackup -File
        foreach ($file in $RootFiles) {
            $TargetFile = Join-Path $ScriptDir "..\$($file.Name)"
            Copy-Item -Path $file.FullName -Destination $TargetFile -Force
            Write-Log "Restored $($file.Name)"
        }
    } else {
        Write-Log "No config backup found in $BackupPath" -Level "WARN"
    }
}

# Function to restore data
function Restore-Data {
    param([string]$BackupPath, [bool]$Force)
    
    $DataBackup = Join-Path $BackupPath "data"
    if (!(Test-Path $DataBackup)) {
        Write-Log "No data backup found in $BackupPath" -Level "INFO"
        return
    }
    
    if (!$Force) {
        $Confirm = Read-Host "Restore data directories? This will overwrite existing data. (y/N)"
        if ($Confirm -ne "y" -and $Confirm -ne "Y") {
            Write-Log "Data restore cancelled by user"
            return
        }
    }
    
    Write-Log "Restoring data directories..."
    
    $TargetData = Join-Path $ScriptDir "..\data"
    
    # Neo4j data
    $Neo4jSource = Join-Path $DataBackup "neo4j"
    $Neo4jTarget = Join-Path $TargetData "neo4j"
    if (Test-Path $Neo4jSource) {
        if (Test-Path $Neo4jTarget) {
            Remove-Item -Path $Neo4jTarget -Recurse -Force
        }
        Copy-Item -Path $Neo4jSource -Destination $Neo4jTarget -Recurse -Force
        Write-Log "Restored Neo4j data"
    }
    
    # Captures
    $CapturesSource = Join-Path $DataBackup "captures"
    $CapturesTarget = Join-Path $TargetData "captures"
    if (Test-Path $CapturesSource) {
        if (Test-Path $CapturesTarget) {
            Remove-Item -Path $CapturesTarget -Recurse -Force
        }
        Copy-Item -Path $CapturesSource -Destination $CapturesTarget -Recurse -Force
        Write-Log "Restored capture data"
    }
}

# Function to perform rollback
function Start-Rollback {
    param([string]$BackupName, [bool]$Force)
    
    Write-Log "========================================"
    Write-Log "Starting Rollback Operation"
    Write-Log "========================================"
    
    # Find backup by name or use latest
    if ([string]::IsNullOrEmpty($BackupName)) {
        $Backups = Get-ChildItem -Path $BackupDir -Directory | Sort-Object CreationTime -Descending
        if ($Backups.Count -eq 0) {
            Write-Log "No backups found to rollback to" -Level "ERROR"
            return
        }
        $BackupPath = $Backups[0].FullName
        $BackupName = $Backups[0].Name
    } else {
        $BackupPath = Join-Path $BackupDir $BackupName
    }
    
    Write-Log "Rolling back to: $BackupName"
    Write-Log "Backup path: $BackupPath"
    
    # Validate backup
    if (!(Test-Backup -BackupPath $BackupPath)) {
        Write-Log "Backup validation failed" -Level "ERROR"
        return
    }
    
    # Stop services before rollback
    Write-Log "Stopping services..."
    & docker-compose down 2>$null
    
    # Restore configurations
    Restore-Configs -BackupPath $BackupPath
    
    # Restore data (with confirmation)
    Restore-Data -BackupPath $BackupPath -Force $Force
    
    Write-Log "========================================"
    Write-Log "Rollback completed successfully!"
    Write-Log "========================================"
    Write-Log "Next steps:"
    Write-Log "  1. Review any configuration changes"
    Write-Log "  2. Restart services: docker-compose up -d"
    Write-Log "  3. Verify system functionality"
}

# Main execution
if ($Help) {
    Write-Host "N-Xyme Catalyst Rollback Script"
    Write-Host "=============================="
    Write-Host ""
    Write-Host "Usage: .\rollback.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -TargetBackup <name>  Rollback to specific backup"
    Write-Host "  -ListBackups          List all available backups"
    Write-Host "  -Force                Skip confirmation prompts"
    Write-Host "  -Help                 Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\rollback.ps1 -ListBackups"
    Write-Host "  .\rollback.ps1 -TargetBackup 2024-01-15_10-30-00"
    Write-Host "  .\rollback.ps1 -TargetBackup 2024-01-15_10-30-00 -Force"
    exit 0
}

try {
    if ($ListBackups) {
        List-Backups
        exit 0
    }
    
    if ([string]::IsNullOrEmpty($TargetBackup)) {
        Write-Host "Usage: .\rollback.ps1 [-TargetBackup <name>] [-ListBackups] [-Force] [-Help]"
        Write-Host "  Use -Help for detailed usage information"
        exit 0
    }
    
    Start-Rollback -BackupName $TargetBackup -Force $Force
}
catch {
    Write-Log "FATAL ERROR: Rollback failed: $_" -Level "ERROR"
    exit 1
}
