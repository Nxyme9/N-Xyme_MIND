# catalyst-daemon.ps1 - Background daemon for N-Xyme Catalyst
# Detects OpenCode via WMI events, auto-starts services with health checks
# Zero CPU while idle (event-driven, no polling)

param(
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"

# ─── Configuration ────────────────────────────────────────────────────────────

$ProjectRoot = "D:\01_CODING\00_N-Xyme_CATALYST"
$LogsDir = Join-Path $ProjectRoot "logs"
$LogFile = Join-Path $LogsDir "catalyst-daemon.log"
$ReadyFlag = Join-Path $ProjectRoot ".catalyst-ready"

$env:JAVA_HOME = "C:\Users\N-Xyme\jdk17\jdk-17.0.12+7"
$env:NEO4J_HOME = "C:\Users\N-Xyme\neo4j\neo4j-community-5.22.0"
$env:PATH = "$($env:JAVA_HOME)\bin;$($env:PATH)"

# Service configuration
$Services = @{
    Neo4j = @{
        Tier = "CRITICAL"
        HealthUrl = "http://localhost:7474"
        HealthPort = 7687
        StartCommand = { 
            $neo4jBat = Join-Path $env:NEO4J_HOME "bin\neo4j.bat"
            Start-Process -FilePath $neo4jBat -ArgumentList "console" -WindowStyle Hidden
        }
        MaxRetries = 3
        RetryDelay = 10
    }
    Ollama = @{
        Tier = "IMPORTANT"
        HealthUrl = "http://localhost:11434/api/tags"
        StartCommand = {
            $ollamaExe = "C:\Users\N-Xyme\AppData\Local\Programs\Ollama\ollama.exe"
            Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        }
        MaxRetries = 3
        RetryDelay = 5
    }
    PM2 = @{
        Tier = "IMPORTANT"
        HealthCheck = { pm2 list 2>&1 | Out-Null; return ($LASTEXITCODE -eq 0) }
        StartCommand = {
            pm2 resurrect 2>&1 | Out-Null
        }
        MaxRetries = 2
        RetryDelay = 5
    }
    Graphiti = @{
        Tier = "OPTIONAL"
        HealthUrl = "http://localhost:8001/health"
        DependsOn = "Neo4j"
        MaxRetries = 2
        RetryDelay = 5
    }
}

# ─── Logging ──────────────────────────────────────────────────────────────────

function Write-DaemonLog {
    param([string]$Message, [string]$Level = "INFO")
    
    $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $logLine = "[$ts] [$Level] $Message"
    
    if (-not (Test-Path $LogsDir)) {
        New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
    }
    
    Add-Content -Path $LogFile -Value $logLine -ErrorAction SilentlyContinue
    
    if ($Verbose) {
        $color = switch ($Level) {
            "ERROR" { "Red" }
            "WARN"  { "Yellow" }
            "OK"    { "Green" }
            default { "Gray" }
        }
        Write-Host $logLine -ForegroundColor $color
    }
}

# ─── Mutex (Single Instance) ─────────────────────────────────────────────────

function Test-Mutex {
    $script:Mutex = $null
    try {
        $script:Mutex = [System.Threading.Mutex]::new($false, "Global\CatalystDaemon")
        if (-not $script:Mutex.WaitOne(0, $false)) {
            Write-DaemonLog "Another instance is already running. Exiting." "WARN"
            return $false
        }
        Write-DaemonLog "Acquired mutex Global\CatalystDaemon" "OK"
        return $true
    } catch {
        Write-DaemonLog "Failed to acquire mutex: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Release-Mutex {
    if ($script:Mutex) {
        try {
            $script:Mutex.ReleaseMutex()
            $script:Mutex.Dispose()
            Write-DaemonLog "Released mutex Global\CatalystDaemon" "INFO"
        } catch {
            Write-DaemonLog "Error releasing mutex: $($_.Exception.Message)" "WARN"
        }
    }
}

# ─── Health Checks ────────────────────────────────────────────────────────────

function Test-HttpHealth {
    param([string]$Url, [int]$TimeoutSec = 5)
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        return ($response.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Test-PortHealth {
    param([int]$Port)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $result = $tcp.BeginConnect("localhost", $Port, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne(1000)
        $tcp.Close()
        return $success
    } catch {
        return $false
    }
}

function Test-ServiceHealth {
    param([string]$ServiceName)
    
    $svc = $Services[$ServiceName]
    
    # Check dependencies first
    if ($svc.DependsOn) {
        $depHealthy = Test-ServiceHealth -ServiceName $svc.DependsOn
        if (-not $depHealthy) {
            Write-DaemonLog "$ServiceName depends on $($svc.DependsOn) which is not healthy" "WARN"
            return $false
        }
    }
    
    # Custom health check
    if ($svc.HealthCheck) {
        return (& $svc.HealthCheck)
    }
    
    # HTTP health check
    if ($svc.HealthUrl) {
        return (Test-HttpHealth -Url $svc.HealthUrl)
    }
    
    # Port check (fallback)
    if ($svc.HealthPort) {
        return (Test-PortHealth -Port $svc.HealthPort)
    }
    
    return $false
}

# ─── Service Management ──────────────────────────────────────────────────────

function Start-ServiceWithRetry {
    param([string]$ServiceName)
    
    $svc = $Services[$ServiceName]
    $tier = $svc.Tier
    $maxRetries = $svc.MaxRetries
    $retryDelay = $svc.RetryDelay
    
    Write-DaemonLog "Starting $ServiceName (Tier: $tier)..." "INFO"
    
    for ($attempt = 1; $attempt -le $maxRetries; $attempt++) {
        # Check if already healthy
        if (Test-ServiceHealth -ServiceName $ServiceName) {
            Write-DaemonLog "$ServiceName already healthy" "OK"
            return $true
        }
        
        # Start the service
        try {
            & $svc.StartCommand
            Write-DaemonLog "$ServiceName start command executed (attempt $attempt/$maxRetries)" "INFO"
        } catch {
            Write-DaemonLog "$ServiceName start failed: $($_.Exception.Message)" "ERROR"
        }
        
        # Wait for health
        $waitTime = 0
        $maxWait = $retryDelay * 3
        while ($waitTime -lt $maxWait) {
            Start-Sleep -Seconds 2
            $waitTime += 2
            if (Test-ServiceHealth -ServiceName $ServiceName) {
                Write-DaemonLog "$ServiceName healthy after ${waitTime}s" "OK"
                return $true
            }
        }
        
        Write-DaemonLog "$ServiceName not healthy after attempt $attempt, retrying in ${retryDelay}s..." "WARN"
        Start-Sleep -Seconds $retryDelay
    }
    
    Write-DaemonLog "$ServiceName FAILED to start after $maxRetries attempts" "ERROR"
    return $false
}

function Start-AllServices {
    # Load cross-session context
    Write-DaemonLog "Loading session context from Graphiti..." "INFO"
    $ctx_result = python -c "import sys; sys.path.insert(0, 'src'); from context_injector import ContextInjector; ci=ContextInjector(); ctx=ci.get_context('preferences velocity decisions',limit=5); print(f'{len(ctx.episodes)} episodes loaded')" 2>/dev/null
    Write-DaemonLog "Context: $ctx_result" "INFO"

    Write-DaemonLog "=== Starting all services ===" "INFO"
    
    $results = @{
        Critical = @()
        Important = @()
        Optional = @()
    }
    
    # Start CRITICAL services first
    foreach ($name in $Services.Keys) {
        if ($Services[$name].Tier -eq "CRITICAL") {
            $ok = Start-ServiceWithRetry -ServiceName $name
            $results.Critical += @{ Name = $name; Healthy = $ok }
        }
    }
    
    # Check if critical services are healthy
    $criticalHealthy = $results.Critical | Where-Object { $_.Healthy -eq $false }
    if ($criticalHealthy) {
        Write-DaemonLog "CRITICAL services failed: $($criticalHealthy.Name -join ', ')" "ERROR"
        Write-DaemonLog "Cannot proceed without critical services" "ERROR"
        return $false
    }
    
    # Start IMPORTANT services
    foreach ($name in $Services.Keys) {
        if ($Services[$name].Tier -eq "IMPORTANT") {
            $ok = Start-ServiceWithRetry -ServiceName $name
            $results.Important += @{ Name = $name; Healthy = $ok }
        }
    }
    
    # Start OPTIONAL services
    foreach ($name in $Services.Keys) {
        if ($Services[$name].Tier -eq "OPTIONAL") {
            $ok = Start-ServiceWithRetry -ServiceName $name
            $results.Optional += @{ Name = $name; Healthy = $ok }
        }
    }
    
    # Log summary
    $criticalOk = ($results.Critical | Where-Object { $_.Healthy }).Count
    $importantOk = ($results.Important | Where-Object { $_.Healthy }).Count
    $optionalOk = ($results.Optional | Where-Object { $_.Healthy }).Count
    
    Write-DaemonLog "Services started: Critical=$criticalOk/$($results.Critical.Count), Important=$importantOk/$($results.Important.Count), Optional=$optionalOk/$($results.Optional.Count)" "INFO"
    
    # Write ready flag if critical + important services are healthy
    $criticalAllHealthy = ($results.Critical | Where-Object { -not $_.Healthy }).Count -eq 0
    $importantAllHealthy = ($results.Important | Where-Object { -not $_.Healthy }).Count -eq 0
    
    if ($criticalAllHealthy -and $importantAllHealthy) {
        Write-DaemonLog "All critical and important services healthy. Writing .catalyst-ready flag" "OK"
        "ready" | Set-Content -Path $ReadyFlag -Encoding UTF8
        return $true
    } else {
        Write-DaemonLog "Not all critical/important services healthy. Skipping ready flag." "WARN"
        return $false
    }
}

function Stop-Services {
    Write-DaemonLog "=== Services continuing (not stopping on OpenCode close) ===" "INFO"
    # Per requirements: DO NOT kill services when OpenCode closes
    # Services persist, we just delete the ready flag
    if (Test-Path $ReadyFlag) {
        Remove-Item -Path $ReadyFlag -Force
        Write-DaemonLog "Deleted .catalyst-ready flag" "INFO"
    }
}

function Restart-UnhealthyServices {
    Write-DaemonLog "=== Checking services for restart ===" "INFO"
    
    foreach ($name in $Services.Keys) {
        if (-not (Test-ServiceHealth -ServiceName $name)) {
            Write-DaemonLog "$name is unhealthy, attempting restart..." "WARN"
            
            # Only restart CRITICAL and IMPORTANT services
            if ($Services[$name].Tier -in @("CRITICAL", "IMPORTANT")) {
                $ok = Start-ServiceWithRetry -ServiceName $name
                if ($ok) {
                    Write-DaemonLog "$name restarted successfully" "OK"
                } else {
                    Write-DaemonLog "$name restart FAILED" "ERROR"
                }
            } else {
                Write-DaemonLog "$name (OPTIONAL) unhealthy, skipping auto-restart" "INFO"
            }
        }
    }
    
    # Update ready flag
    $criticalHealthy = ($Services.Keys | Where-Object { 
        $Services[$_].Tier -eq "CRITICAL" -and (Test-ServiceHealth -ServiceName $_)
    }).Count
    $importantHealthy = ($Services.Keys | Where-Object { 
        $Services[$_].Tier -eq "IMPORTANT" -and (Test-ServiceHealth -ServiceName $_)
    }).Count
    $criticalTotal = ($Services.Keys | Where-Object { $Services[$_].Tier -eq "CRITICAL" }).Count
    $importantTotal = ($Services.Keys | Where-Object { $Services[$_].Tier -eq "IMPORTANT" }).Count
    
    if (($criticalHealthy -eq $criticalTotal) -and ($importantHealthy -eq $importantTotal)) {
        if (-not (Test-Path $ReadyFlag)) {
            Write-DaemonLog "All critical+important healthy, writing .catalyst-ready flag" "OK"
            "ready" | Set-Content -Path $ReadyFlag -Encoding UTF8
        }
    } else {
        if (Test-Path $ReadyFlag) {
            Write-DaemonLog "Services degraded, removing .catalyst-ready flag" "WARN"
            Remove-Item -Path $ReadyFlag -Force
        }
    }
}

# ─── WMI Event Watcher ───────────────────────────────────────────────────────

function Start-WmiWatcher {
    Write-DaemonLog "Starting WMI event watcher for opencode.exe..." "INFO"
    
    # Register WMI event for opencode.exe process creation
    $query = "SELECT * FROM Win32_ProcessStartTrace WHERE ProcessName='opencode.exe'"
    
    try {
        $null = Register-CimIndicationEvent -Query $query -SourceIdentifier "OpenCodeStarted" -Action {
            $processId = $Event.SourceEventArgs.NewEvent.ProcessID
            Write-DaemonLog "Detected opencode.exe (PID: $processId)" "OK"
            
            # Start all services
            $global:OpenCodeDetected = $true
        }
        
        Write-DaemonLog "WMI watcher registered successfully" "OK"
        return $true
    } catch {
        Write-DaemonLog "Failed to register WMI watcher: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Stop-WmiWatcher {
    try {
        $event = Get-EventSubscriber -SourceIdentifier "OpenCodeStarted" -ErrorAction SilentlyContinue
        if ($event) {
            Unregister-Event -SourceIdentifier "OpenCodeStarted"
            Write-DaemonLog "WMI watcher unregistered" "INFO"
        }
    } catch {
        Write-DaemonLog "Error unregistering WMI watcher: $($_.Exception.Message)" "WARN"
    }
}

# ─── Main Loop ────────────────────────────────────────────────────────────────

function Start-Daemon {
    Write-DaemonLog "========================================" "INFO"
    Write-DaemonLog "N-Xyme Catalyst Daemon Starting" "INFO"
    Write-DaemonLog "========================================" "INFO"
    
    # Check single instance
    if (-not (Test-Mutex)) {
        return
    }
    
    try {
        # Start WMI watcher
        if (-not (Start-WmiWatcher)) {
            Write-DaemonLog "Failed to start WMI watcher. Exiting." "ERROR"
            return
        }
        
        $global:OpenCodeDetected = $false
        $servicesStarted = $false
        
        Write-DaemonLog "Daemon ready. Waiting for opencode.exe..." "OK"
        Write-DaemonLog "Zero CPU while idle (event-driven)" "INFO"
        
        # Main monitoring loop
        while ($true) {
            # Check if OpenCode was detected
            if ($global:OpenCodeDetected -and -not $servicesStarted) {
                Write-DaemonLog "OpenCode detected! Starting services..." "OK"
                $servicesStarted = Start-AllServices
                $global:OpenCodeDetected = $false
            }
            
            # Check if OpenCode is still running
            if ($servicesStarted) {
                $opencodeRunning = Get-Process -Name "opencode" -ErrorAction SilentlyContinue
                
                if (-not $opencodeRunning) {
                    Write-DaemonLog "OpenCode closed. Removing ready flag, returning to WMI watch." "INFO"
                    Stop-Services
                    $servicesStarted = $false
                } else {
                    # Periodic health check (every 30s)
                    Restart-UnhealthyServices
                }
            }
            
            # Process any pending WMI events
            $event = Get-Event -SourceIdentifier "OpenCodeStarted" -ErrorAction SilentlyContinue
            if ($event) {
                Remove-Event -SourceIdentifier "OpenCodeStarted" -ErrorAction SilentlyContinue
                $global:OpenCodeDetected = $true
            }
            
            Start-Sleep -Seconds 30
        }
    } catch [System.Management.Automation.PipelineStoppedException] {
        Write-DaemonLog "Daemon stopped by user (Ctrl+C)" "WARN"
    } catch {
        Write-DaemonLog "Daemon crashed: $($_.Exception.Message)" "ERROR"
        Write-DaemonLog "Stack: $($_.ScriptStackTrace)" "ERROR"
    } finally {
        Stop-WmiWatcher
        Release-Mutex
        
        if (Test-Path $ReadyFlag) {
            Remove-Item -Path $ReadyFlag -Force
        }
        
        Write-DaemonLog "========================================" "INFO"
        Write-DaemonLog "Catalyst Daemon Stopped" "INFO"
        Write-DaemonLog "========================================" "INFO"
    }
}

# ─── Entry Point ──────────────────────────────────────────────────────────────

Start-Daemon

# Run distill-memory on startup (background)
Write-HeartbeatLog "Distilling memory..."
Start-Job -ScriptBlock {
    python "D:_CODING _N-Xyme_CATALYST\scripts\distill-memory.py"
} | Out-Null

# Run episode backfill on startup (background)
Write-HeartbeatLog "Starting episode backfill..."
Start-Job -ScriptBlock {
    python "D:\01_CODING\00_N-Xyme_CATALYST\scripts\backfill-episodes.py"
} | Out-Null
