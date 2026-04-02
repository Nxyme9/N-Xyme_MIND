# N-Xyme Catalyst Heartbeat Monitor
# Tests all services every 30 seconds

$API_KEY = "h1_2qaF6NEK1XjNCNho1ToJvdmL5eRMJNEluKGOMBxg"
$INTERVAL = 30

function Test-Service {
    param($Name, $Url, $Method = "GET", $Headers = @{}, $Body = $null)
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            Headers = $Headers
            TimeoutSec = 5
            UseBasicParsing = $true
        }
        if ($Body) {
            $params.Body = $Body
            $params.ContentType = "application/json"
        }
        $response = Invoke-WebRequest @params
        if ($response.StatusCode -eq 200) {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

while ($true) {
    Clear-Host
    Write-Host "=== N-Xyme Catalyst Heartbeat Monitor ===" -ForegroundColor Cyan
    Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Cyan
    
    # Test Graphiti
    if (Test-Service "Graphiti" "http://localhost:8001/health") {
        Write-Host "[OK] Graphiti Memory" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Graphiti Memory" -ForegroundColor Red
    }
    
    # Test Ollama
    if (Test-Service "Ollama" "http://localhost:11434/api/tags") {
        Write-Host "[OK] Ollama AI" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Ollama AI" -ForegroundColor Red
    }
    
    # Test Jarvis API
    if (Test-Service "Jarvis API" "http://localhost:8088/health") {
        Write-Host "[OK] Jarvis API" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Jarvis API" -ForegroundColor Red
    }
    
    # Test Jarvis Status
    $headers = @{ "Authorization" = "Bearer $API_KEY" }
    if (Test-Service "Jarvis Status" "http://localhost:8088/status" -Headers $headers) {
        Write-Host "[OK] Jarvis Status" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Jarvis Status" -ForegroundColor Red
    }
    
    # Test Command API
    $body = @{ message = "test" } | ConvertTo-Json
    if (Test-Service "Command API" "http://localhost:8088/command" -Method POST -Headers $headers -Body $body) {
        Write-Host "[OK] Command API" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Command API" -ForegroundColor Red
    }
    
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Next test in $INTERVAL seconds..." -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
    
    Start-Sleep -Seconds $INTERVAL
}
