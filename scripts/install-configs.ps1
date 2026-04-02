# Install configuration files to system locations
# This script copies configs from the repository to the appropriate system directories

param(
    [switch]$Help,
    [switch]$Force
)

if ($Help) {
    Write-Host "Usage: .\install-configs.ps1 [-Force]"
    Write-Host "  -Force  Overwrite existing configurations"
    exit
}

# Configuration mapping
$configs = @{
    # OpenCode agent configurations
    "configs/opencode/agents/core-infra.yaml" = "$env:USERPROFILE\.config\opencode\agents\core-infra.yaml"
    "configs/opencode/agents/graphiti.yaml" = "$env:USERPROFILE\.config\opencode\agents\graphiti.yaml"
    "configs/opencode/agents/framework.yaml" = "$env:USERPROFILE\.config\opencode\agents\framework.yaml"
    "configs/opencode/agents/security.yaml" = "$env:USERPROFILE\.config\opencode\agents\security.yaml"
    "configs/opencode/agents/auto-capture.yaml" = "$env:USERPROFILE\.config\opencode\agents\auto-capture.yaml"
    "configs/opencode/agents/mcp-local.yaml" = "$env:USERPROFILE\.config\opencode\agents\mcp-local.yaml"
    "configs/opencode/agents/mcp-web.yaml" = "$env:USERPROFILE\.config\opencode\agents\mcp-web.yaml"
    "configs/opencode/agents/mcp-utility.yaml" = "$env:USERPROFILE\.config\opencode\agents\mcp-utility.yaml"
    "configs/opencode/agents/performance.yaml" = "$env:USERPROFILE\.config\opencode\agents\performance.yaml"
    "configs/opencode/agents/monitoring.yaml" = "$env:USERPROFILE\.config\opencode\agents\monitoring.yaml"
    
    # Plugin configurations
    "configs/opencode/plugins/graphiti.json" = "$env:USERPROFILE\.config\opencode\plugins\graphiti.json"
    "configs/opencode/plugins/security-agent.json" = "$env:USERPROFILE\.config\opencode\plugins\security-agent.json"
    "configs/opencode/plugins/github-mcp.json" = "$env:USERPROFILE\.config\opencode\plugins\github-mcp.json"
    "configs/opencode/plugins/git-mcp.json" = "$env:USERPROFILE\.config\opencode\plugins\git-mcp.json"
    "configs/opencode/plugins/sqlite-mcp.json" = "$env:USERPROFILE\.config\opencode\plugins\sqlite-mcp.json"
    "configs/opencode/plugins/playwright-mcp.json" = "$env:USERPROFILE\.config\opencode\plugins\playwright-mcp.json"
    "configs/opencode/plugins/puppeteer-mcp.json" = "$env:USERPROFILE\.config\opencode\plugins\puppeteer-mcp.json"
    "configs/opencode/plugins/fetch-mcp.json" = "$env:USERPROFILE\.config\opencode\plugins\fetch-mcp.json"
    "configs/opencode/plugins/brave-mcp.json" = "$env:USERPROFILE\.config\opencode\plugins\brave-mcp.json"
    "configs/opencode/plugins/exa-mcp.json" = "$env:USERPROFILE\.config\opencode\plugins\exa-mcp.json"
    "configs/opencode/plugins/context7-mcp.json" = "$env:USERPROFILE\.config\opencode\plugins\context7-mcp.json"
    "configs/opencode/plugins/grep-app-mcp.json" = "$env:USERPROFILE\.config\opencode\plugins\grep-app-mcp.json"
    "configs/opencode/plugins/obsidian-mcp.json" = "$env:USERPROFILE\.config\opencode\plugins\obsidian-mcp.json"
    "configs/opencode/plugins/shadcn-mcp.json" = "$env:USERPROFILE\.config\opencode\plugins\shadcn-mcp.json"
    
    # Main OpenCode config
    "configs/opencode/opencode.json" = "$env:USERPROFILE\.config\opencode\opencode.json"
    "configs/opencode/permissions.json" = "$env:USERPROFILE\.config\opencode\permissions.json"
    
    # Other configs
    "configs/graphiti/.graphitirc" = "$env:USERPROFILE\.graphitirc"
    "configs/ollama/config.json" = "$env:USERPROFILE\.ollama\config.json"
    "configs/security-agent/config.yaml" = "$env:USERPROFILE\.config\security-agent\config.yaml"
}

# Create directories and copy files
foreach ($source in $configs.Keys) {
    $destination = $configs[$source]
    $destDir = Split-Path -Parent $destination
    
    # Create destination directory if it doesn't exist
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        Write-Host "Created directory: $destDir"
    }
    
    # Check if file already exists
    if (Test-Path $destination) {
        if ($Force) {
            Write-Host "Overwriting: $destination"
            Copy-Item -Path $source -Destination $destination -Force
        } else {
            Write-Host "Skipping (exists): $destination"
        }
    } else {
        Write-Host "Copying: $destination"
        Copy-Item -Path $source -Destination $destination
    }
}

Write-Host "`nConfiguration installation complete."
Write-Host "Remember to replace placeholder values in .env file with actual secrets."