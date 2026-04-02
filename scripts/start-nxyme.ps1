# N-Xyme Catalyst Startup Script for Windows
# This script starts all required services for the N-Xyme Catalyst environment.

param(
    [switch]$Help,
    [switch]$Build,
    [switch]$Detach
)

if ($Help) {
    Write-Host "Usage: .\start-nxyme.ps1 [-Build] [-Detach]"
    Write-Host "  -Build   Rebuild images before starting"
    Write-Host "  -Detach  Run in detached mode"
    exit
}

# Change to the script directory
Set-Location $PSScriptRoot

# Ensure Docker is running
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in PATH. Please install Docker Desktop."
    exit 1
}

# Check if Docker daemon is running
try {
    docker info | Out-Null
} catch {
    Write-Error "Docker daemon is not running. Please start Docker Desktop."
    exit 1
}

# Build images if requested
if ($Build) {
    Write-Host "Building Docker images..."
    docker-compose -f ../docker-compose.yml -f ../docker-compose.override.yml build
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Build failed."
        exit 1
    }
}

# Start services
Write-Host "Starting N-Xyme Catalyst services..."
if ($Detach) {
    docker-compose -f ../docker-compose.yml -f ../docker-compose.override.yml up -d
} else {
    docker-compose -f ../docker-compose.yml -f ../docker-compose.override.yml up
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to start services."
    exit 1
}

Write-Host "N-Xyme Catalyst started successfully."
Write-Host "Services:"
Write-Host "  - Neo4j Browser: http://localhost:7474"
Write-Host "  - Neo4j Bolt: bolt://localhost:7687"
Write-Host "  - Graphiti MCP: http://localhost:8001"
Write-Host ""
Write-Host "To stop services, run: docker-compose -f ../docker-compose.yml -f ../docker-compose.override.yml down"