# Agent PowerShell Launcher
# Opens agents in separate windows for visibility

param(
    [string]$AgentName,
    [string]$Task
)

$Host.UI.RawUI.WindowTitle = "AGENT: $AgentName"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AGENT: $AgentName" -ForegroundColor Yellow
Write-Host "  Started: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "TASK:" -ForegroundColor Green
Write-Host $Task
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "WORKING..." -ForegroundColor Yellow
