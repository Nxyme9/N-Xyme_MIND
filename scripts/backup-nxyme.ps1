# N-Xyme Catalyst Backup Script
# Creates a timestamped backup of configs and data

param(
    [string]$BackupDir = "D:\backups",
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: .\backup-nxyme.ps1 [-BackupDir <path>]"
    Write-Host "  -BackupDir  Directory to store backups (default: D:\backups)"
    exit
}

# Create backup directory if it doesn't exist
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

# Generate timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupName = "nxyme_$timestamp"
$backupPath = Join-Path -Path $BackupDir -ChildPath $backupName

# Create backup directory
New-Item -ItemType Directory -Path $backupPath -Force | Out-Null

Write-Host "Creating backup: $backupPath"

# Stop services for consistent backup
Write-Host "Stopping services..."
docker-compose -f "$PSScriptRoot\..\docker-compose.yml" -f "$PSScriptRoot\..\docker-compose.override.yml" down

# Backup configs
Write-Host "Backing up configs..."
Copy-Item -Recurse -Path "$PSScriptRoot\..\configs\" -Destination "$backupPath\configs\"

# Backup data
Write-Host "Backing up data..."
Copy-Item -Recurse -Path "$PSScriptRoot\..\data\" -Destination "$backupPath\data\"

# Backup Docker volumes (if any)
Write-Host "Backing up Docker volumes..."
docker volume ls -q | ForEach-Object {
    $volume = $_
    if ($volume -like "*nxyme*") {
        Write-Host "Backing up volume: $volume"
        docker run --rm -v ${volume}:/volume -v ${backupPath}:/backup alpine tar czf /backup/${volume}.tar.gz -C /volume ./
    }
}

# Start services again
Write-Host "Starting services..."
docker-compose -f "$PSScriptRoot\..\docker-compose.yml" -f "$PSScriptRoot\..\docker-compose.override.yml" up -d

# Create archive
Write-Host "Creating archive..."
$archivePath = "$backupPath.zip"
Compress-Archive -Path $backupPath -DestinationPath $archivePath

# Clean up uncompressed directory
Remove-Item -Recurse -Force $backupPath

Write-Host "`nBackup completed successfully!"
Write-Host "Archive: $archivePath"
Write-Host "Size: $((Get-Item $archivePath).Length / 1MB) MB"

# Cleanup old backups (keep last 7 days)
Write-Host "`nCleaning up old backups..."
$cutoffDate = (Get-Date).AddDays(-7)
Get-ChildItem -Path $BackupDir -Filter "nxyme_*.zip" | Where-Object {
    $_.CreationTime -lt $cutoffDate
} | ForEach-Object {
    Write-Host "Removing old backup: $($_.Name)"
    Remove-Item $_.FullName -Force
}