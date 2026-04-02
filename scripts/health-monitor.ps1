# N-Xyme Catalyst Health Monitor
# Monitors services and auto-restarts if needed

param(
    [int]$Interval = 60,  # Check interval in seconds
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: .\health-monitor.ps1 [-Interval <seconds>]"
    Write-Host "  -Interval  Check interval in seconds (default: 60)"
    exit
}

# Service definitions
$services = @{
    "neo4j" = "http://localhost:7474"
    "graphiti-mcp" = "http://localhost:8001/health"
    "security-agent" = "http://localhost:5002/health"
    "auto-capture" = "http://localhost:5003/health"
}

# Log file
$logFile = "$PSScriptRoot\..\logs\health-monitor.log"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "$timestamp - $Message"
    Write-Host $logEntry
    Add-Content -Path $logFile -Value $logEntry
}

function Test-Service {
    param([string]$Name, [string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            return $true
        }
    } catch {
        Write-Log "ERROR: Service $Name is not responding at $Url"
    }
    return $false
}

function Restart-Service {
    param([string]$Name)
    Write-Log "Restarting service: $Name"
    try {
        docker-compose -f "$PSScriptRoot\..\docker-compose.yml" -f "$PSScriptRoot\..\docker-compose.override.yml" restart $Name
        Write-Log "Service $Name restarted successfully"
    } catch {
        Write-Log "ERROR: Failed to restart service $Name"
    }
}

# Main monitoring loop
Write-Log "Health monitor started with $Interval-second interval"
Write-Log "Monitoring services: $($services.Keys -join ', ')"

while ($true) {
    foreach ($service in $services.Keys) {
        $healthy = Test-Service -Name $service -Url $services[$service]
        
        if (-not $healthy) {
            Write-Log "Service $service is unhealthy, attempting restart..."
            Restart-Service -Name $service
            
            # Wait a moment before checking again
            Start-Sleep -Seconds 5
            
            # Check if restart helped
            $stillUnhealthy = -not (Test-Service -Name $service -Url $services[$service])
            if ($stillUnhealthy) {
                Write-Log "ERROR: Service $service still unhealthy after restart"
            }
        }
    }
    
    Write-Log "Health check completed, waiting $Interval seconds..."
    Start-Sleep -Seconds $Interval
}