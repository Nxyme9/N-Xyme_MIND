# Jarvis Heartbeat Monitor
# Shows real-time system status in a persistent window

$Host.UI.RawUI.WindowTitle = "JARVIS HEARTBEAT MONITOR"
$Host.UI.RawUI.BackgroundColor = "Black"
$Host.UI.RawUI.ForegroundColor = "Green"

# Clear screen
Clear-Host

# Config
$API_KEY = "h1_2qaF6NEK1XjNCNho1ToJvdmL5eRMJNEluKGOMBxg"
$REFRESH_INTERVAL = 5  # seconds

function Show-Header {
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║           JARVIS HEARTBEAT MONITOR v1.0                  ║" -ForegroundColor Cyan
    Write-Host "║           N-Xyme Catalyst                                 ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Show-Timestamp {
    Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Yellow
    Write-Host "Refresh: Every $REFRESH_INTERVAL seconds" -ForegroundColor Gray
    Write-Host ""
}

function Test-Service {
    param($Name, $Url, $Color)
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        Write-Host "  [OK] $Name" -ForegroundColor $Color
        return $true
    } catch {
        Write-Host "  [FAIL] $Name" -ForegroundColor Red
        return $false
    }
}

function Show-Services {
    Write-Host "═══ SERVICES ═══" -ForegroundColor Cyan
    
    $graphiti = Test-Service "Graphiti Memory" "http://localhost:8001/health" "Green"
    $ollama = Test-Service "Ollama AI" "http://localhost:11434/api/tags" "Green"
    $jarvis = Test-Service "Jarvis API" "http://localhost:8088/health" "Green"
    
    # Check Neo4j
    $neo4j = netstat -ano | Select-String "7687" | Select-String "LISTENING"
    if ($neo4j) {
        Write-Host "  [OK] Neo4j Database" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Neo4j Database" -ForegroundColor Red
    }
    
    # Check Auto-capture
    $autocapture = netstat -ano | Select-String "5003" | Select-String "LISTENING"
    if ($autocapture) {
        Write-Host "  [OK] Auto-capture" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Auto-capture (port 5003)" -ForegroundColor Yellow
    }
    
    Write-Host ""
}

function Show-Resources {
    Write-Host "═══ RESOURCES ═══" -ForegroundColor Cyan
    
    # CPU
    $cpu = (Get-WmiObject Win32_Processor).LoadPercentage
    $cpuColor = if ($cpu -gt 80) { "Red" } elseif ($cpu -gt 60) { "Yellow" } else { "Green" }
    Write-Host "  CPU:    $cpu%" -ForegroundColor $cpuColor
    
    # Memory
    $os = Get-WmiObject Win32_OperatingSystem
    $memTotal = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    $memFree = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    $memUsed = [math]::Round($memTotal - $memFree, 2)
    $memPercent = [math]::Round(($memUsed / $memTotal) * 100, 0)
    $memColor = if ($memPercent -gt 80) { "Red" } elseif ($memPercent -gt 60) { "Yellow" } else { "Green" }
    Write-Host "  Memory: $memUsed GB / $memTotal GB ($memPercent%)" -ForegroundColor $memColor
    
    # GPU
    try {
        $gpu = nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader 2>$null
        if ($gpu) {
            $gpuParts = $gpu -split ", "
            $gpuUtil = $gpuParts[0].Replace(" %", "")
            $gpuMem = "$($gpuParts[1]) / $($gpuParts[2])"
            $gpuColor = if ($gpuUtil -gt 80) { "Red" } elseif ($gpuUtil -gt 60) { "Yellow" } else { "Green" }
            Write-Host "  GPU:    $gpuUtil% | $gpuMem" -ForegroundColor $gpuColor
        }
    } catch {
        Write-Host "  GPU:    N/A" -ForegroundColor Gray
    }
    
    Write-Host ""
}

function Show-Agents {
    Write-Host "═══ ACTIVE AGENTS ═══" -ForegroundColor Cyan
    
    $pythonProcesses = Get-Process -Name python -ErrorAction SilentlyContinue
    if ($pythonProcesses) {
        foreach ($proc in $pythonProcesses) {
            $cpu = [math]::Round($proc.CPU, 1)
            $mem = [math]::Round($proc.WorkingSet64 / 1MB, 0)
            Write-Host "  PID $($proc.Id): CPU ${cpu}s | Memory ${mem}MB" -ForegroundColor White
        }
    } else {
        Write-Host "  No agents running" -ForegroundColor Gray
    }
    
    Write-Host ""
}

function Show-Pending {
    Write-Host "═══ PENDING ISSUES ═══" -ForegroundColor Cyan
    
    # Read from global issues file
    $issuesFile = "D:\01_CODING\00_N-Xyme_CATALYST\.sisyphus\notepads\global-issues-roi.md"
    if (Test-Path $issuesFile) {
        $content = Get-Content $issuesFile -Raw
        
        # Extract critical issues
        if ($content -match "CRITICAL.*?(\d+)\. (.*?)$") {
            Write-Host "  🔴 CRITICAL: $($matches[2])" -ForegroundColor Red
        }
        
        # Extract high issues
        if ($content -match "HIGH.*?(\d+)\. (.*?)$") {
            Write-Host "  🟠 HIGH: $($matches[2])" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  No issues file found" -ForegroundColor Gray
    }
    
    Write-Host ""
}

function Show-Controls {
    Write-Host "═══ CONTROLS ═══" -ForegroundColor Cyan
    Write-Host "  [R] Refresh now" -ForegroundColor White
    Write-Host "  [A] Show all agents" -ForegroundColor White
    Write-Host "  [L] Show logs" -ForegroundColor White
    Write-Host "  [Q] Quit" -ForegroundColor White
    Write-Host ""
}

# Main loop
while ($true) {
    Clear-Host
    Show-Header
    Show-Timestamp
    Show-Services
    Show-Resources
    Show-Agents
    Show-Pending
    Show-Controls
    
    Write-Host "Next refresh in $REFRESH_INTERVAL seconds..." -ForegroundColor Gray
    
    # Wait with key check
    $timeout = $REFRESH_INTERVAL
    while ($timeout -gt 0) {
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            switch ($key.Key) {
                "R" { $timeout = 0 }
                "A" { 
                    Write-Host "`nAll Python processes:" -ForegroundColor Yellow
                    Get-Process -Name python -ErrorAction SilentlyContinue | Format-Table Id, ProcessName, CPU, WorkingSet64
                    Read-Host "Press Enter to continue"
                }
                "L" {
                    Write-Host "`nRecent logs:" -ForegroundColor Yellow
                    Get-Content "D:\01_CODING\00_N-Xyme_CATALYST\logs\*.log" -Tail 20 -ErrorAction SilentlyContinue
                    Read-Host "Press Enter to continue"
                }
                "Q" { exit }
            }
        }
        Start-Sleep -Seconds 1
        $timeout--
    }
}
