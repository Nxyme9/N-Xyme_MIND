#Requires -Version 5.1
<#
.SYNOPSIS
    Graphiti Memory Heartbeat - Monitors and auto-heals the global memory system
.DESCRIPTION
    Continuous health monitoring for Neo4j and Graphiti MCP with auto-healing capabilities
    Runs every 30 seconds, logs to D:\01_CODING\00_N-Xyme_CATALYST\logs\graphiti-heartbeat.log
.NOTES
    Run with: powershell -WindowStyle Hidden -File graphiti-heartbeat.ps1
#>

#region Configuration
$Script:Config = @{
    # Paths
    LogPath = "D:\01_CODING\00_N-Xyme_CATALYST\logs\graphiti-heartbeat.log"
    Neo4jStartScript = "C:\Users\N-Xyme\neo4j\start-neo4j-bg.bat"
    DataDir = "D:\01_CODING\00_N-Xyme_CATALYST"

    # Endpoints
    Neo4jHttp = "http://localhost:7474"
    Neo4jBolt = "localhost:7687"
    GraphitiMcp = "http://localhost:8001"
    GraphitiRpc = "http://localhost:8001/json-rpc"

    # Timing (milliseconds)
    CheckInterval = 30000
    HttpTimeout = 5000

    # Thresholds
    EpisodeDropThreshold = 0.10  # 10% drop triggers alert
    RestartCooldown = 60000     # 60s between restarts
}

# State tracking
$Script:State = @{
    LastEpisodeCount = 0
    LastRestartTime = 0
    LastRestartReason = ""
    RestartCount = @{
        Neo4j = 0
        Graphiti = 0
    }
    TestEpisodeId = "heartbeat-test-$(Get-Date -Format 'yyyyMMddHHmmss')"
}

#endregion

#region Logging
function Write-HeartbeatLog {
    param(
        [string]$Message,
        [ValidateSet('INFO', 'WARN', 'ERROR', 'SUCCESS', 'HEAL')]
        [string]$Level = 'INFO'
    )

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $logEntry = "[$timestamp] [$Level] $Message"

    # Ensure log directory exists
    $logDir = Split-Path $Script:Config.LogPath -Parent
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    # Write to file
    Add-Content -Path $Script:Config.LogPath -Value $logEntry

    # Also output to console for debugging
    Write-Host $logEntry
}

#endregion

#region Health Checks
function Test-Neo4jHttp {
    try {
        $response = Invoke-WebRequest -Uri $Script:Config.Neo4jHttp -Method Get `
            -TimeoutSec ($Script:Config.HttpTimeout / 1000) -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Test-Neo4jBolt {
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.Connect($Script:Config.Neo4jBolt.Split(':')[0], [int]$Script:Config.Neo4jBolt.Split(':')[1])
        $tcpClient.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Test-GraphitiMcpHealth {
    try {
        $response = Invoke-WebRequest -Uri "$($Script:Config.GraphitiMcp)/health" -Method Get `
            -TimeoutSec ($Script:Config.HttpTimeout / 1000) -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Test-GraphitiCanRead {
    try {
        $body = @{
            jsonrpc = "2.0"
            id = 1
            method = "tools/list"
            params = @{}
        } | ConvertTo-Json

        $response = Invoke-WebRequest -Uri $Script:Config.GraphitiRpc -Method Post `
            -Body $body -ContentType "application/json" `
            -TimeoutSec ($Script:Config.HttpTimeout / 1000) -UseBasicParsing

        $result = $response.Content | ConvertFrom-Json
        return $result.result -ne $null
    }
    catch {
        return $false
    }
}

function Test-GraphitiCanWrite {
    try {
        $testEpisode = @{
            jsonrpc = "2.0"
            id = 2
            method = "tools/call"
            params = @{
                name = "graphiti_add_episode"
                arguments = @{
                    source_info = @{
                        episode = @{
                            name = $Script:State.TestEpisodeId
                            summary = "Graphiti Heartbeat Test Episode"
                            facts = @("heartbeat-test-fact-1", "heartbeat-test-fact-2")
                        }
                        agent = "graphiti-heartbeat"
                    }
                }
            }
        } | ConvertTo-Json -Depth 3

        $response = Invoke-WebRequest -Uri $Script:Config.GraphitiRpc -Method Post `
            -Body $testEpisode -ContentType "application/json" `
            -TimeoutSec ($Script:Config.HttpTimeout / 1000) -UseBasicParsing

        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Test-GraphitiCanSearch {
    try {
        $searchRequest = @{
            jsonrpc = "2.0"
            id = 3
            method = "tools/call"
            params = @{
                name = "graphiti_search"
                arguments = @{
                    query = $Script:State.TestEpisodeId
                    top_k = 5
                }
            }
        } | ConvertTo-Json -Depth 3

        $response = Invoke-WebRequest -Uri $Script:Config.GraphitiRpc -Method Post `
            -Body $searchRequest -ContentType "application/json" `
            -TimeoutSec ($Script:Config.HttpTimeout / 1000) -UseBasicParsing

        $result = $response.Content | ConvertFrom-Json
        return $result.result -ne $null
    }
    catch {
        return $false
    }
}

function Get-GraphitiEpisodeCount {
    try {
        # Query Neo4j for episode count via Graphiti's knowledge graph
        $countRequest = @{
            jsonrpc = "2.0"
            id = 4
            method = "tools/call"
            params = @{
                name = "graphiti_get_stats"
                arguments = @{}
            }
        } | ConvertTo-Json

        $response = Invoke-WebRequest -Uri $Script:Config.GraphitiRpc -Method Post `
            -Body $countRequest -ContentType "application/json" `
            -TimeoutSec ($Script:Config.HttpTimeout / 1000) -UseBasicParsing

        $result = $response.Content | ConvertFrom-Json
        if ($result.result.respond_episodes) {
            return [int]$result.result.respond_episodes
        }
        return 0
    }
    catch {
        # Fallback: try direct Neo4j query
        try {
            $query = "MATCH (e:Episode) RETURN count(e) as count"
            # This would require Neo4j driver - fallback to return -1 as unknown
            return -1
        }
        catch {
            return -1
        }
    }
}

function Test-EpisodeCountStable {
    param([int]$CurrentCount)

    if ($Script:State.LastEpisodeCount -eq 0) {
        # First run, just set baseline
        $Script:State.LastEpisodeCount = $CurrentCount
        return $true
    }

    if ($CurrentCount -le 0) {
        return $false  # Invalid count
    }

    $dropPercent = ($Script:State.LastEpisodeCount - $CurrentCount) / $Script:State.LastEpisodeCount
    $Script:State.LastEpisodeCount = $CurrentCount

    if ($dropPercent -gt $Script:Config.EpisodeDropThreshold) {
        Write-HeartbeatLog "Episode count dropped from $($Script:State.LastEpisodeCount) to $CurrentCount ($([math]::Round($dropPercent * 100, 1))% drop)" -Level 'WARN'
        return $false
    }

    return $true
}

#endregion

#region Auto-Heal Actions
function Start-Neo4jRestart {
    $now = Get-Date
    if (($now - (Get-Date $Script:State.LastRestartTime)).TotalMilliseconds -lt $Script:Config.RestartCooldown) {
        Write-HeartbeatLog "Neo4j restart cooldown active, skipping restart" -Level 'INFO'
        return $false
    }

    Write-HeartbeatLog "Attempting to restart Neo4j..." -Level 'HEAL'

    if (Test-Path $Script:Config.Neo4jStartScript) {
        try {
            Start-Process -FilePath $Script:Config.Neo4jStartScript -WindowStyle Hidden
            $Script:State.RestartCount.Neo4j++
            $Script:State.LastRestartTime = $now
            $Script:State.LastRestartReason = "Neo4j HTTP/Bolt failed"
            Write-HeartbeatLog "Neo4j restart initiated" -Level 'HEAL'
            return $true
        }
        catch {
            Write-HeartbeatLog "Failed to start Neo4j: $_" -Level 'ERROR'
            return $false
        }
    }
    else {
        Write-HeartbeatLog "Neo4j start script not found: $($Script:Config.Neo4jStartScript)" -Level 'ERROR'
        return $false
    }
}

function Start-GraphitiRestart {
    $now = Get-Date
    if (($now - (Get-Date $Script:State.LastRestartTime)).TotalMilliseconds -lt $Script:Config.RestartCooldown) {
        Write-HeartbeatLog "Graphiti restart cooldown active, skipping restart" -Level 'INFO'
        return $false
    }

    Write-HeartbeatLog "Attempting to restart Graphiti MCP..." -Level 'HEAL'

    try {
        # Use pm2 to restart graphiti-mcp
        $process = Start-Process -FilePath "pm2" -ArgumentList "restart graphiti-mcp" `
            -NoNewWindow -Wait -PassThru

        if ($process.ExitCode -eq 0) {
            $Script:State.RestartCount.Graphiti++
            $Script:State.LastRestartTime = $now
            $Script:State.LastRestartReason = "Graphiti health check failed"
            Write-HeartbeatLog "Graphiti restart via pm2 successful" -Level 'HEAL'
            return $true
        }
        else {
            Write-HeartbeatLog "pm2 restart failed with exit code $($process.ExitCode)" -Level 'ERROR'
            return $false
        }
    }
    catch {
        Write-HeartbeatLog "Failed to restart Graphiti: $_" -Level 'ERROR'
        return $false
    }
}

#endregion

#region Main Health Check Routine
function Invoke-HealthCheck {
    Write-HeartbeatLog "=== Starting Health Check Cycle ===" -Level 'INFO'

    $checks = @{
        Neo4jHttp = $false
        Neo4jBolt = $false
        GraphitiMcpHealth = $false
        GraphitiCanRead = $false
        GraphitiCanWrite = $false
        GraphitiCanSearch = $false
        EpisodeCountStable = $false
    }

    # 1. Neo4j HTTP
    Write-HeartbeatLog "Checking Neo4j HTTP (port 7474)..." -Level 'INFO'
    $checks.Neo4jHttp = Test-Neo4jHttp
    Write-HeartbeatLog "Neo4j HTTP: $(if($checks.Neo4jHttp){'OK'}else{'FAILED'})" `
        -Level $(if($checks.Neo4jHttp){'SUCCESS'}else{'ERROR'})

    # 2. Neo4j Bolt
    Write-HeartbeatLog "Checking Neo4j Bolt (port 7687)..." -Level 'INFO'
    $checks.Neo4jBolt = Test-Neo4jBolt
    Write-HeartbeatLog "Neo4j Bolt: $(if($checks.Neo4jBolt){'OK'}else{'FAILED'})" `
        -Level $(if($checks.Neo4jBolt){'SUCCESS'}else{'ERROR'})

    # 3. Graphiti MCP Health
    Write-HeartbeatLog "Checking Graphiti MCP health endpoint..." -Level 'INFO'
    $checks.GraphitiMcpHealth = Test-GraphitiMcpHealth
    Write-HeartbeatLog "Graphiti MCP Health: $(if($checks.GraphitiMcpHealth){'OK'}else{'FAILED'})" `
        -Level $(if($checks.GraphitiMcpHealth){'SUCCESS'}else{'ERROR'})

    # 4. Graphiti Can Read
    Write-HeartbeatLog "Checking Graphiti read capability (tools/list)..." -Level 'INFO'
    $checks.GraphitiCanRead = Test-GraphitiCanRead
    Write-HeartbeatLog "Graphiti Can Read: $(if($checks.GraphitiCanRead){'OK'}else{'FAILED'})" `
        -Level $(if($checks.GraphitiCanRead){'SUCCESS'}else{'ERROR'})

    # 5. Graphiti Can Write
    Write-HeartbeatLog "Checking Graphiti write capability..." -Level 'INFO'
    $checks.GraphitiCanWrite = Test-GraphitiCanWrite
    Write-HeartbeatLog "Graphiti Can Write: $(if($checks.GraphitiCanWrite){'OK'}else{'FAILED'})" `
        -Level $(if($checks.GraphitiCanWrite){'SUCCESS'}else{'ERROR'})

    # 6. Graphiti Can Search
    Write-HeartbeatLog "Checking Graphiti search capability..." -Level 'INFO'
    $checks.GraphitiCanSearch = Test-GraphitiCanSearch
    Write-HeartbeatLog "Graphiti Can Search: $(if($checks.GraphitiCanSearch){'OK'}else{'FAILED'})" `
        -Level $(if($checks.GraphitiCanSearch){'SUCCESS'}else{'ERROR'})

    # 7. Episode Count (only if Graphiti is working)
    if ($checks.GraphitiCanRead) {
        $episodeCount = Get-GraphitiEpisodeCount
        Write-HeartbeatLog "Current episode count: $episodeCount" -Level 'INFO'
        $checks.EpisodeCountStable = Test-EpisodeCountStable -CurrentCount $episodeCount
        Write-HeartbeatLog "Episode Count Stable: $(if($checks.EpisodeCountStable){'OK'}else{'WARNING - DATA LOSS SUSPECTED'})" `
            -Level $(if($checks.EpisodeCountStable){'SUCCESS'}else{'WARN'})
    }

    # Determine overall health
    $allHealthy = $checks.Values -notcontains $false

    if ($allHealthy) {
        Write-HeartbeatLog "=== All health checks PASSED ===" -Level 'SUCCESS'
    }
    else {
        Write-HeartbeatLog "=== Health checks FAILED - initiating auto-heal ===" -Level 'ERROR'

        # Auto-heal logic
        if (-not $checks.Neo4jHttp -or -not $checks.Neo4jBolt) {
            Write-HeartbeatLog "Neo4j is down, attempting restart..." -Level 'WARN'
            Start-Neo4jRestart
        }

        if (-not $checks.GraphitiMcpHealth -or -not $checks.GraphitiCanRead) {
            Write-HeartbeatLog "Graphiti MCP is unresponsive, attempting restart..." -Level 'WARN'
            Start-GraphitiRestart
        }

        if (-not $checks.GraphitiCanWrite) {
            Write-HeartbeatLog "Graphiti write failed, attempting restart..." -Level 'WARN'
            Start-GraphitiRestart
        }

        if (-not $checks.GraphitiCanSearch) {
            Write-HeartbeatLog "Graphiti search failed, attempting restart..." -Level 'WARN'
            Start-GraphitiRestart
        }

        if (-not $checks.EpisodeCountStable) {
            Write-HeartbeatLog "Episode count dropped significantly - possible data loss" -Level 'WARN'
        }
    }

    # Log restart stats
    Write-HeartbeatLog "Total restarts - Neo4j: $($Script:State.RestartCount.Neo4j), Graphiti: $($Script:State.RestartCount.Graphiti)" -Level 'INFO'

    return $allHealthy
}

#endregion

#region Main Loop
function Start-Heartbeat {
    Write-HeartbeatLog "========================================" -Level 'INFO'
    Write-HeartbeatLog "Graphiti Heartbeat Started" -Level 'INFO'
    Write-HeartbeatLog "Log file: $($Script:Config.LogPath)" -Level 'INFO'
    Write-HeartbeatLog "Check interval: $($Script:Config.CheckInterval / 1000) seconds" -Level 'INFO'
    Write-HeartbeatLog "========================================" -Level 'INFO'

    # Initial health check
    Invoke-HealthCheck

    # Continuous loop
    while ($true) {
        Start-Sleep -Milliseconds $Script:Config.CheckInterval

        try {
            Invoke-HealthCheck | Out-Null
        }
        catch {
            Write-HeartbeatLog "Health check cycle error: $_" -Level 'ERROR'
        }
    }
}

# Trap for graceful shutdown
trap {
    Write-HeartbeatLog "Heartbeat received stop signal, shutting down gracefully..." -Level 'INFO'
    exit 0
}

# Start the heartbeat
Start-Heartbeat