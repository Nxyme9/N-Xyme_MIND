# Start all Utility MCP Servers for N-Xyme Catalyst
# This script starts the Context7, Grep-app, Obsidian, and Shadcn MCP servers locally.

$ErrorActionPreference = "Stop"

# Set the working directory to the project root
Set-Location (Split-Path $PSScriptRoot -Parent)

# Define the servers
$servers = @(
    @{ Name = "Context7"; Path = "packages/mcp-servers/utility-tools/context7-mcp"; Port = 12020 },
    @{ Name = "Grep-app"; Path = "packages/mcp-servers/utility-tools/grep-app-mcp"; Port = 12021 },
    @{ Name = "Obsidian"; Path = "packages/mcp-servers/utility-tools/obsidian-mcp"; Port = 12022 },
    @{ Name = "Shadcn"; Path = "packages/mcp-servers/utility-tools/shadcn-mcp"; Port = 12023 }
)

foreach ($server in $servers) {
    Write-Host "Starting $($server.Name) MCP server on port $($server.Port)..."
    # Start each server in a new PowerShell window (so they run independently)
    # We'll also redirect output to a log file
    $logFile = "$($server.Path)\server.log"
    $processArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", "Set-Location '$($server.Path)'; npm start 2>&1 | Tee-Object -FilePath '$logFile'"
    )
    Start-Process powershell.exe -ArgumentList $processArgs -WindowStyle Hidden
    Start-Sleep -Seconds 2  # Give time for server to start
}

Write-Host "All MCP servers started. Check logs in each server directory."
