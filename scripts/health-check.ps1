# N-Xyme Catalyst Health Check
# Safe health monitoring - read-only checks

param(
    [switch]$Verbose,
    [switch]$Continuous
)

$ErrorActionPreference = "Continue"

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Host "----------------------------------------" -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host "----------------------------------------" -ForegroundColor Cyan
}

function Write-Status {
    param([string]$Name, [string]$Status, [string]$Detail = "")
    $color = switch ($Status) {
        "[OK]" { "Green" }
        "[FAIL]" { "Red" }
        "[WARN]" { "Yellow" }
        default { "White" }
    }
    Write-Host "  $Status $Name" -ForegroundColor $color -NoNewline
    if ($Detail) { Write-Host " - $Detail" -ForegroundColor Gray }
    else { Write-Host "" }
}

# Header
Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  N-Xyme Catalyst - Health Check" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "===========================================================" -ForegroundColor Cyan

# System Resources
Write-Section "System Resources"

# CPU
$cpu = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 1 -ErrorAction SilentlyContinue).CounterSamples.CookedValue
if ($cpu -ne $null) {
    $cpuRounded = [math]::Round($cpu, 1)
    $cpuStatus = if ($cpu -gt 90) { "[FAIL]" } elseif ($cpu -gt 70) { "[WARN]" } else { "[OK]" }
    Write-Host "  CPU Usage: $cpuRounded% " -NoNewline
    if ($cpuStatus -eq "[OK]") { Write-Host "$cpuStatus" -ForegroundColor Green }
    elseif ($cpuStatus -eq "[WARN]") { Write-Host "$cpuStatus" -ForegroundColor Yellow }
    else { Write-Host "$cpuStatus" -ForegroundColor Red }
}

# RAM
$ram = Get-CimInstance Win32_OperatingSystem
$ramUsed = [math]::Round(($ram.TotalVisibleMemorySize - $ram.FreePhysicalMemory) / 1MB, 1)
$ramTotal = [math]::Round($ram.TotalVisibleMemorySize / 1MB, 1)
$ramPercent = [math]::Round($ramUsed / $ramTotal * 100, 1)
$ramStatus = if ($ramPercent -gt 90) { "[FAIL]" } elseif ($ramPercent -gt 75) { "[WARN]" } else { "[OK]" }
Write-Host "  RAM Usage: $ramUsed GB / $ramTotal GB ($ramPercent%) " -NoNewline
Write-Host "$ramStatus" -ForegroundColor $ramStatus

# GPU (if available)
Write-Section "GPU Status (RTX 3080 Ti)"
try {
    $gpuOutput = nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader 2>&1
    if ($gpuOutput -match "NVIDIA") {
        $gpuInfo = $gpuOutput -split ","
        Write-Host "  GPU: $(($gpuInfo[0]).Trim())" -ForegroundColor White
        Write-Host "  Utilization: $(($gpuInfo[1]).Trim())" -ForegroundColor White
        Write-Host "  Memory: $(($gpuInfo[2]).Trim()) / $(($gpuInfo[3]).Trim())" -ForegroundColor White
        Write-Host "  Temperature: $(($gpuInfo[4]).Trim())" -ForegroundColor White
        Write-Status "GPU" "[OK]" "Active"
    }
} catch {
    Write-Status "GPU" "[WARN]" "nvidia-smi not available"
}

# Ollama
Write-Section "Ollama Service"
$ollamaRunning = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($ollamaRunning) {
    Write-Status "Ollama" "[OK]" "Running (PID: $($ollamaRunning.Id))"
    
    if ($Verbose) {
        Write-Host ""
        Write-Host "  Loaded Models:" -ForegroundColor Yellow
        $models = ollama ps 2>&1
        if ($models -match "NAME") {
            $models -split "`n" | Where-Object { $_ -notmatch "^$" -and $_ -notmatch "NAME" } | ForEach-Object {
                Write-Host "    $_" -ForegroundColor Gray
            }
        }
    }
} else {
    Write-Status "Ollama" "[FAIL]" "Not running"
}

# OpenCode
Write-Section "OpenCode Status"
$opencodeRunning = Get-Process -Name "opencode" -ErrorAction SilentlyContinue
if ($opencodeRunning) {
    Write-Status "OpenCode" "[OK]" "Running (PID: $($opencodeRunning.Id))"
    
    if ($Verbose) {
        $cpuCores = $opencodeRunning.ProcessorAffinity
        Write-Host "    CPU Affinity: $cpuCores" -ForegroundColor Gray
        $memMB = [math]::Round($opencodeRunning.WorkingSet64 / 1MB, 0)
        Write-Host "    Memory: $memMB MB" -ForegroundColor Gray
    }
} else {
    Write-Status "OpenCode" "[WARN]" "Not currently running"
}

# MCP Servers
Write-Section "MCP Servers"
Write-Host "  Checking MCP status..." -ForegroundColor Gray
$mcpOutput = opencode mcp list 2>&1 | Out-String
$connected = ($mcpOutput -split "`n" | Where-Object { $_ -match "[OK]" }).Count
$failed = ($mcpOutput -split "`n" | Where-Object { $_ -match "[FAIL]" }).Count
$total = ($mcpOutput -split "`n" | Where-Object { $_ -match "\[OK\]|\[FAIL\]" }).Count

Write-Host "  Total: $total | Connected: $connected | Failed: $failed" -ForegroundColor White
if ($Verbose -and $failed -gt 0) {
    Write-Host ""
    Write-Host "  Failed Servers:" -ForegroundColor Yellow
    $mcpOutput -split "`n" | Where-Object { $_ -match "[FAIL]" } | ForEach-Object {
        if ($_ -match "^\s*\[FAIL\]\s*(.+)") {
            Write-Host "    - $($matches[1])" -ForegroundColor Red
        }
    }
}

# Agents
Write-Section "OpenCode Agents"
Write-Host "  Checking agent status..." -ForegroundColor Gray
$agentOutput = opencode agent list 2>&1 | Out-String
$agentCount = ($agentOutput -split "`n" | Where-Object { $_ -match "\(" }).Count
Write-Host "  Total Agents: $agentCount" -ForegroundColor White

if ($Verbose) {
    Write-Host ""
    Write-Host "  Primary Agents:" -ForegroundColor Yellow
    $agentOutput -split "`n" | Where-Object { $_ -match "primary\)" } | ForEach-Object {
        $agent = $_ -replace "\s*\(primary\)", ""
        Write-Host "    [OK] $agent" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "  Subagents:" -ForegroundColor Gray
    $agentOutput -split "`n" | Where-Object { $_ -match "subagent\)" } | ForEach-Object {
        $agent = $_ -replace "\s*\(subagent\)", ""
        Write-Host "    - $agent" -ForegroundColor Gray
    }
}

# Neo4j (if running)
Write-Section "Neo4j (Graphiti Backend)"
$neo4jRunning = Get-Process -Name "neo4j" -ErrorAction SilentlyContinue
if ($neo4jRunning) {
    Write-Status "Neo4j" "[OK]" "Running"
} else {
    $neo4jService = Get-Service -Name "Neo4j" -ErrorAction SilentlyContinue
    if ($neo4jService) {
        Write-Status "Neo4j Service" $(
            switch ($neo4jService.Status) {
                "Running" { "[OK]" }
                "Stopped" { "[FAIL]" }
                default { "[WARN]" }
            }
        ) $neo4jService.Status
    } else {
        Write-Status "Neo4j" "[WARN]" "Not installed or not running"
    }
}

# Summary
Write-Section "Summary"
$issues = 0
if (-not $ollamaRunning) { $issues++ }
if (-not $opencodeRunning) { $issues++ }
if ($failed -gt 0) { $issues += $failed }

if ($issues -eq 0) {
    Write-Host "  [OK] All systems operational" -ForegroundColor Green
} else {
    Write-Host "  [WARN] $issues issue(s) detected" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Quick fixes:" -ForegroundColor Yellow
    if (-not $ollamaRunning) { Write-Host "    .\scripts\start-nxyme-master.ps1" -ForegroundColor Gray }
    if (-not $opencodeRunning) { Write-Host "    opencode" -ForegroundColor Gray }
}

Write-Host ""
