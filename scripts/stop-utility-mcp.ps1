# Stop all Utility MCP Servers for N-Xyme Catalyst

$ErrorActionPreference = "Stop"

# Set the working directory to the project root
Set-Location (Split-Path $PSScriptRoot -Parent)

# Define the server directories
$serverDirs = @(
    "packages/mcp-servers/utility-tools/context7-mcp",
    "packages/mcp-servers/utility-tools/grep-app-mcp",
    "packages/mcp-servers/utility-tools/obsidian-mcp",
    "packages/mcp-servers/utility-tools/shadcn-mcp"
)

foreach ($dir in $serverDirs) {
    Write-Host "Stopping server in $dir..."
    # Find node processes running in that directory
    $nodeProcesses = Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*$dir*" }
    foreach ($proc in $nodeProcesses) {
        Stop-Process -Id $proc.Id -Force
        Write-Host "Stopped process $($proc.Id)"
    }
}

Write-Host "All MCP servers stopped."
