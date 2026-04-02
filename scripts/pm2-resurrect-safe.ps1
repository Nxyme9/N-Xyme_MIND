<#
.SYNOPSIS
    Safe PM2 resurrect that waits for Neo4j before starting processes.
.DESCRIPTION
    Called by pm2-windows-startup at login to prevent graphiti-mcp
    from starting before Neo4j bolt port (7687) is ready.
#>

$neo4jHost = "localhost"
$neo4jPort = 7687
$maxWaitSec = 60
$pollIntervalSec = 2
$logFile = Join-Path $env:PM2_HOME "resurrect-safe.log"

function Write-Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

Write-Log "=== pm2-resurrect-safe: Starting ==="
Write-Log "Waiting for Neo4j on $neo4jHost`:$neo4jPort (max ${maxWaitSec}s)..."

$elapsed = 0
$neo4jReady = $false

while ($elapsed -lt $maxWaitSec) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $result = $tcp.BeginConnect($neo4jHost, $neo4jPort, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne(1000, $false)
        if ($success -and $tcp.Connected) {
            $tcp.EndConnect($result)
            $tcp.Close()
            $neo4jReady = $true
            Write-Log "Neo4j is ready after ${elapsed}s."
            break
        }
        $tcp.Close()
    } catch {
        # Connection failed, keep polling
    }
    Write-Log "Neo4j not ready yet (${elapsed}s elapsed)..."
    Start-Sleep -Seconds $pollIntervalSec
    $elapsed += $pollIntervalSec
}

if (-not $neo4jReady) {
    Write-Log "WARNING: Neo4j not responding after ${maxWaitSec}s. Proceeding with pm2 resurrect anyway."
}

Write-Log "Running pm2 resurrect..."
$pm2Home = if ($env:PM2_HOME) { $env:PM2_HOME } else { Join-Path $env:USERPROFILE ".pm2" }
$dumpPath = Join-Path $pm2Home "dump.pm2"

if (-not (Test-Path $dumpPath)) {
    Write-Log "ERROR: PM2 dump not found at $dumpPath"
    exit 1
}

pm2 resurrect
if ($LASTEXITCODE -eq 0) {
    Write-Log "SUCCESS: pm2 resurrect completed."
} else {
    Write-Log "ERROR: pm2 resurrect failed with exit code $LASTEXITCODE."
}

Write-Log "=== pm2-resurrect-safe: Done ==="
exit $LASTEXITCODE
