# N-Xyme Catalyst Heartbeat Test Script
# Tests all services automatically every 30 seconds

$ErrorActionPreference = "Continue"
$API_KEY = "h1_2qaF6NEK1XjNCNho1ToJvdmL5eRMJNEluKGOMBxg"
$INTERVAL = 30  # seconds

function Write-Status {
    param($Service, $Status, $Details)
    $color = if ($Status -eq "OK") { "Green" } else { "Red" }
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Service : " -NoNewline
    Write-Host $Status -ForegroundColor $color -NoNewline
    Write-Host " - $Details"
}

function Test-Service {
    param($Name, $Url, $Headers = @{})
    try {
        $response = Invoke-WebRequest -Uri $Url -Headers $Headers -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            return @{ Status = "OK"; Details = $response.Content.Substring(0, [Math]::Min(50, $response.Content.Length)) }
        }
    } catch {
        return @{ Status = "FAIL"; Details = $_.Exception.Message }
    }
    return @{ Status = "FAIL"; Details = "Unknown error" }
}

function Test-AllServices {
    Write-Host "`n=== HEARTBEAT TEST - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -ForegroundColor Cyan
    
    # Test Graphiti
    $result = Test-Service "Graphiti" "http://localhost:8001/health"
    Write-Status "Graphiti Memory" $result.Status $result.Details
    
    # Test Ollama
    $result = Test-Service "Ollama" "http://localhost:11434/api/tags"
    Write-Status "Ollama AI" $result.Status $result.Details
    
    # Test Jarvis API
    $result = Test-Service "Jarvis API" "http://localhost:8088/health"
    Write-Status "Jarvis API" $result.Status $result.Details
    
    # Test Jarvis Status (with auth)
    $headers = @{ "Authorization" = "Bearer $API_KEY" }
    $result = Test-Service "Jarvis Status" "http://localhost:8088/status" $headers
    Write-Status "Jarvis Status" $result.Status $result.Details
    
    # Test Chat API
    $result = Test-Service "Chat API" "http://localhost:8088/chat" $headers
    Write-Status "Chat API" $result.Status $result.Details
    
    # Test Command API
    try {
        $body = @{ message = "Heartbeat test" } | ConvertTo-Json
        $response = Invoke-WebRequest -Uri "http://localhost:8088/command" -Method POST -Headers $headers -Body $body -ContentType "application/json" -TimeoutSec 5 -UseBasicParsing
        Write-Status "Command API" "OK" "Command accepted"
    } catch {
        Write-Status "Command API" "FAIL" $_.Exception.Message
    }
    
    Write-Host "=== END HEARTBEAT TEST ===`n" -ForegroundColor Cyan
}

# Main loop
Write-Host "Starting Heartbeat Test Monitor..." -ForegroundColor Yellow
Write-Host "Testing every $INTERVAL seconds. Press Ctrl+C to stop." -ForegroundColor Yellow

while ($true) {
    Test-AllServices
    Start-Sleep -Seconds $INTERVAL
}
