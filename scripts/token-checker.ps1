# OpenCode Zen Token Checker
# Check remaining tokens on OpenCode Zen API

param(
    [string]$ApiKey = "",
    [switch]$Watch
)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OpenCode Zen Token Checker" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check API key
if ([string]::IsNullOrEmpty($ApiKey)) {
    $envKey = $env:OPENCODE_ZEN_API_KEY
    if ([string]::IsNullOrEmpty($envKey)) {
        Write-Host "[ERROR] No API key provided" -ForegroundColor Red
        Write-Host ""
        Write-Host "Usage:" -ForegroundColor Yellow
        Write-Host "  .\token-checker.ps1 -ApiKey 'your-key'"
        Write-Host "  Or set environment variable: $env:OPENCODE_ZEN_API_KEY"
        exit 1
    }
    $ApiKey = $envKey
}

Write-Host "[INFO] Using API key: $($ApiKey.Substring(0, 8))..." -ForegroundColor Cyan
Write-Host ""

function Get-ZenStatus {
    param([string]$Key)
    
    try {
        $headers = @{
            "Authorization" = "Bearer $Key"
            "Content-Type" = "application/json"
        }
        
        # Try to get models list
        $response = Invoke-WebRequest -Uri "https://opencode.ai/zen/v1/models" -Headers $headers -Method GET -TimeoutSec 15
        
        if ($response.StatusCode -eq 200) {
            return @{
                Status = "ok"
                Message = "API responding normally"
                Data = $response.Content
            }
        }
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        $errorMsg = $_.Exception.Message
        
        return @{
            Status = "error"
            StatusCode = $statusCode
            Message = $errorMsg
        }
    }
    
    return @{ Status = "unknown" }
}

function Test-ZenModel {
    param([string]$Key, [string]$Model = "zenmux/xiaomi/mimo-v2-flash-free")
    
    try {
        $headers = @{
            "Authorization" = "Bearer $Key"
            "Content-Type" = "application/json"
        }
        
        $body = @{
            model = $Model
            messages = @(
                @{ role = "user"; content = "Hi" }
            )
            max_tokens = 5
        } | ConvertTo-Json
        
        $response = Invoke-WebRequest -Uri "https://opencode.ai/zen/v1/chat/completions" -Headers $headers -Method POST -Body $body -TimeoutSec 30
        
        if ($response.StatusCode -eq 200) {
            $data = $response.Content | ConvertFrom-Json
            return @{
                Status = "ok"
                Tokens = $data.usage.total_tokens
                Model = $Model
            }
        }
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        
        if ($statusCode -eq 429) {
            return @{ Status = "rate_limited"; Model = $Model }
        }
        elseif ($statusCode -eq 401 -or $statusCode -eq 403) {
            return @{ Status = "auth_error"; Model = $Model }
        }
        else {
            return @{ Status = "error"; StatusCode = $statusCode; Model = $Model }
        }
    }
    
    return @{ Status = "unknown"; Model = $Model }
}

# Check status
Write-Host "[INFO] Checking Zen API status..." -ForegroundColor Yellow

$status = Get-ZenStatus -Key $ApiKey

Write-Host ""
switch ($status.Status) {
    "ok" {
        Write-Host "[OK] Zen API is responding" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "[INFO] Testing model access..." -ForegroundColor Yellow
        $modelTest = Test-ZenModel -Key $ApiKey
        
        Write-Host ""
        switch ($modelTest.Status) {
            "ok" {
                Write-Host "[OK] Model accessible - Tokens used in test: $($modelTest.Tokens)" -ForegroundColor Green
            }
            "rate_limited" {
                Write-Host "[WARN] Rate limited! Need VPN rotation." -ForegroundColor Red
            }
            "auth_error" {
                Write-Host "[ERROR] Authentication failed! Check your API key." -ForegroundColor Red
            }
            default {
                Write-Host "[WARN] Model test returned: $($modelTest.Status)" -ForegroundColor Yellow
            }
        }
    }
    "rate_limited" {
        Write-Host "[WARN] Rate limited! Need VPN rotation." -ForegroundColor Red
    }
    "depleted" {
        Write-Host "[ERROR] Tokens depleted! Need VPN rotation." -ForegroundColor Red
    }
    "auth_error" {
        Write-Host "[ERROR] Authentication failed! Check your API key." -ForegroundColor Red
    }
    default {
        Write-Host "[WARN] API returned: $($status.Status)" -ForegroundColor Yellow
        Write-Host "[INFO] Message: $($status.Message)" -ForegroundColor Cyan
    }
}

Write-Host ""

# Watch mode
if ($Watch) {
    Write-Host "[INFO] Watch mode enabled. Checking every 60 seconds..." -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
    Write-Host ""
    
    while ($true) {
        Start-Sleep -Seconds 60
        $timestamp = Get-Date -Format "HH:mm:ss"
        Write-Host "[$timestamp] Re-checking..." -NoNewline
        
        $newStatus = Get-ZenStatus -Key $ApiKey
        
        if ($newStatus.Status -eq "ok") {
            Write-Host " OK" -ForegroundColor Green
        } else {
            Write-Host " $($newStatus.Status.ToUpper())" -ForegroundColor Red
        }
    }
}
