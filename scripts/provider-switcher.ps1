# Provider Switcher - Smart model switching based on availability
# Switches between Local (Ollama) and Zen (Free tokens)

param(
    [ValidateSet("auto", "local", "zen")]
    [string]$Mode = "auto",
    [switch]$ShowStatus
)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OpenCode Provider Switcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$script:currentProvider = "local"

function Get-ProviderStatus {
    $status = @{
        Local = @{ Available = $false; Model = "" }
        Zen = @{ Available = $false; Tokens = "unknown" }
    }
    
    # Check Ollama
    try {
        $ollamaModels = ollama list 2>$null
        if ($ollamaModels) {
            $status.Local.Available = $true
            $status.Local.Models = ($ollamaModels | Select-Object -First 5) -join ", "
        }
    } catch {
        $status.Local.Available = $false
    }
    
    # Check Zen tokens
    $zenKey = $env:OPENCODE_ZEN_API_KEY
    if ([string]::IsNullOrEmpty($zenKey)) {
        $status.Zen.Available = $false
        $status.Zen.Tokens = "No API key"
    } else {
        try {
            $headers = @{ "Authorization" = "Bearer $zenKey" }
            $response = Invoke-WebRequest -Uri "https://opencode.ai/zen/v1/models" -Headers $headers -Method GET -TimeoutSec 10
            if ($response.StatusCode -eq 200) {
                $status.Zen.Available = $true
                $status.Zen.Tokens = "Available"
            }
        } catch {
            if ($_.Exception.Response.StatusCode.value__ -eq 429) {
                $status.Zen.Available = $false
                $status.Zen.Tokens = "Depleted"
            } else {
                $status.Zen.Available = $false
                $status.Zen.Tokens = "Error"
            }
        }
    }
    
    return $status
}

function Switch-Provider {
    param([string]$To)
    
    $configPath = "$HOME\.config\opencode\opencode.json"
    $configDir = Split-Path -Parent $configPath
    
    Write-Host ""
    Write-Host "[SWITCH] Switching to: $To" -ForegroundColor Yellow
    
    switch ($To) {
        "local" {
            $configFile = "$configDir\opencode-local.json"
        }
        "zen" {
            $configFile = "$configDir\opencode-zen.json"
        }
        "hybrid" {
            $configFile = "$configDir\opencode-hybrid.json"
        }
    }
    
    if (Test-Path $configFile) {
        Copy-Item -Path $configFile -Destination $configPath -Force
        Write-Host "[OK] Switched to $To provider" -ForegroundColor Green
        $script:currentProvider = $To
    } else {
        Write-Host "[ERROR] Config file not found: $configFile" -ForegroundColor Red
    }
}

function Get-AutoSwitchRecommendation {
    param($Status)
    
    # Priority logic
    if ($Status.Local.Available) {
        return "local"
    }
    
    if ($Status.Zen.Available) {
        return "zen"
    }
    
    return "none"
}

# Show status if requested
if ($ShowStatus -or $Mode -eq "auto") {
    Write-Host "[INFO] Checking provider status..." -ForegroundColor Yellow
    $status = Get-ProviderStatus
    
    Write-Host ""
    Write-Host "Local (Ollama):" -ForegroundColor Cyan
    if ($status.Local.Available) {
        Write-Host "  Status: Available" -ForegroundColor Green
        Write-Host "  Models: $($status.Local.Models)" -ForegroundColor White
    } else {
        Write-Host "  Status: Not available" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Zen (Free):" -ForegroundColor Cyan
    Write-Host "  Status: $($status.Zen.Tokens)" -ForegroundColor $(if ($status.Zen.Available) { "Green" } else { "Red" })
    
    Write-Host ""
    
    if ($Mode -eq "auto") {
        $recommendation = Get-AutoSwitchRecommendation -Status $status
        Write-Host "[INFO] Recommended provider: $recommendation" -ForegroundColor Cyan
        
        if ($recommendation -ne $script:currentProvider) {
            Switch-Provider -To $recommendation
        }
    }
}

# Manual switch
if ($Mode -ne "auto") {
    Switch-Provider -To $Mode
}

Write-Host ""
Write-Host "[INFO] Current provider: $script:currentProvider" -ForegroundColor Cyan
Write-Host ""
