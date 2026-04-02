# PRE_WIN11_INVENTORY.ps1
# Script to create a complete inventory before Windows 11 upgrade
# Author: N-Xyme
# Created: $(Get-Date -Format 'yyyy-MM-dd')

# Set up backup directory with timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = "D:\01_CODING\00_N-Xyme_CATALYST\backup\Win11_prepare_$timestamp"
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

Write-Host "=== Windows 11 Pre-Upgrade Inventory ==="
Write-Host "Backup directory: $BackupDir"
Write-Host ""

# Section A: Complete Software Inventory
Write-Host "Section A: Collecting installed programs..."

# Installed Programs (using Get-Package - note: may require running as admin for some packages)
try {
    Get-Package | Select-Object Name, Version, ProviderName | Sort-Object Name | Export-Csv "$BackupDir\installed_programs.csv" -NoTypeInformation
    Write-Host "  Installed programs exported to installed_programs.csv"
} catch {
    Write-Warning "  Could not get installed packages via Get-Package: $_"
    # Fallback to wmic or registry if needed
}

# VS Code Extensions
if (Get-Command code -ErrorAction SilentlyContinue) {
    try {
        code --list-extensions > "$BackupDir\vscode_extensions.txt"
        Write-Host "  VS Code extensions exported to vscode_extensions.txt"
    } catch {
        Write-Warning "  Could not list VS Code extensions: $_"
    }
} else {
    Write-Warning "  VS Code (code) not found in PATH"
}

# npm global packages
if (Get-Command npm -ErrorAction SilentlyContinue) {
    try {
        npm list -g --depth=0 --json > "$BackupDir\npm_global.json"
        Write-Host "  NPM global packages exported to npm_global.json"
    } catch {
        Write-Warning "  Could not list npm global packages: $_"
    }
} else {
    Write-Warning "  npm not found in PATH"
}

# pip packages
if (Get-Command pip -ErrorAction SilentlyContinue) {
    try {
        pip freeze > "$BackupDir\pip_packages.txt"
        Write-Host "  PIP packages exported to pip_packages.txt"
    } catch {
        Write-Warning "  Could not list pip packages: $_"
    }
} else {
    Write-Warning "  pip not found in PATH"
}

# Cargo packages
if (Get-Command cargo -ErrorAction SilentlyContinue) {
    try {
        cargo install --list > "$BackupDir\cargo_packages.txt"
        Write-Host "  Cargo packages exported to cargo_packages.txt"
    } catch {
        Write-Warning "  Could not list cargo packages: $_"
    }
} else {
    Write-Warning "  cargo not found in PATH"
}

# dotnet tools
if (Get-Command dotnet -ErrorAction SilentlyContinue) {
    try {
        dotnet tool list -g > "$BackupDir\dotnet_tools.txt"
        Write-Host "  Dotnet tools exported to dotnet_tools.txt"
    } catch {
        Write-Warning "  Could not list dotnet tools: $_"
    }
} else {
    Write-Warning "  dotnet not found in PATH"
}

# WSL distros list
if (Get-Command wsl -ErrorAction SilentlyContinue) {
    try {
        wsl --list --verbose > "$BackupDir\wsl_distros.txt"
        Write-Host "  WSL distros exported to wsl_distros.txt"
    } catch {
        Write-Warning "  Could not list WSL distros: $_"
    }
} else {
    Write-Warning "  wsl not found in PATH"
}

Write-Host ""

# Section B: VST/Plugin Discovery
Write-Host "Section B: Discovering VST/plugin locations..."

$VSTPaths = @(
    "C:\Program Files\VSTPlugins",
    "C:\Program Files\Common Files\VST3",
    "C:\Program Files\Steinberg\VSTPlugins",
    "C:\Program Files\Common Files\Steinberg",
    "C:\Program Files\FL Studio\Plugins",
    "C:\Program Files\Native Instruments",
    "C:\Program Files\Reaper\Plugins",
    "C:\Program Files (x86)\VSTPlugins",
    "C:\Program Files (x86)\Steinberg\VSTPlugins",
    "C:\ProgramData\PluginAlliance",
    "C:\ProgramData\UVI",
    "C:\Users\$env:USERNAME\Documents\Ableton",
    "C:\Users\$env:USERNAME\Documents\VSTPlugins",
    "C:\Users\$env:USERNAME\AppData\Local\VirtualStore\Program Files"
)

$VSTFound = @()
foreach ($path in $VSTPaths) {
    if (Test-Path $path) {
        $VSTFound += $path
        # Get subdirectories or files as needed
        try {
            Get-ChildItem -Path $path -Directory -ErrorAction SilentlyContinue | Select-Object FullName | Export-Csv "$BackupDir\VST_$(($path -replace '[:\\]', '_')).csv" -NoTypeInformation
        } catch {
            # If no subdirectories, just note the path exists
            "$path`t(exists)" | Out-File -FilePath "$BackupDir\VST_$(($path -replace '[:\\]', '_')).txt" -Append
        }
    }
}

# Write VST paths summary
$VSTFound | Out-File "$BackupDir\VST_paths_found.txt"
Write-Host "  Found $($VSTFound.Count) VST plugin paths"

Write-Host ""

# Section C: Ableton-Specific
Write-Host "Section C: Checking Ableton installation..."

$AbletonVersion = Get-ItemProperty "HKLM:\SOFTWARE\Ableton" -ErrorAction SilentlyContinue
if ($AbletonVersion) {
    Write-Host "  Ableton registry key found"
    $AbletonVersion | Out-File "$BackupDir\Ableton_registry.txt"
} else {
    Write-Warning "  Ableton registry key not found in HKLM:\SOFTWARE\Ableton"
}

$AbletonPaths = @(
    "C:\ProgramData\Ableton",
    "$env:USERPROFILE\Documents\Ableton",
    "$env:USERPROFILE\AppData\Roaming\Ableton",
    "C:\Program Files\Ableton"
)

$AbletonFound = @()
foreach ($path in $AbletonPaths) {
    if (Test-Path $path) {
        $AbletonFound += $path
        try {
            Get-ChildItem -Path $path -Recurse -ErrorAction SilentlyContinue | Select-Object FullName, Length | Export-Csv "$BackupDir\Ableton_$(($path -replace '[:\\]', '_')).csv" -NoTypeInformation
        } catch {
            "$path`t(exists)" | Out-File -FilePath "$BackupDir\Ableton_$(($path -replace '[:\\]', '_')).txt" -Append
        }
    }
}

$AbletonFound | Out-File "$BackupDir\Ableton_paths_found.txt"
Write-Host "  Found $($AbletonFound.Count) Ableton-related paths"

Write-Host ""

# Section D: Common Development Tools
Write-Host "Section D: Checking common development tools..."

$DevTools = @{
    Python = @{Locations = @("$env:LOCALAPPDATA\Programs\Python", "C:\Python*"); EnvVar = "PYTHONPATH"}
    Node = @{Locations = @("$env:ProgramFiles\nodejs", "$env:APPDATA\npm")}
    Rust = @{Locations = @("$env:USERPROFILE\.cargo")}
    Go = @{Locations = @("$env:USERPROFILE\go")}
    Java = @{Locations = @("C:\Program Files\Java", "$env:JAVA_HOME")}
    Android = @{Locations = @("$env:LOCALAPPDATA\Android")}
    JetBrains = @{Locations = @("$env:LOCALAPPDATA\JetBrains\Toolbox", "$env:APPDATA\JetBrains")}
    Unity = @{Locations = @("C:\Program Files\Unity*", "$env:APPDATA\Unity")}
    Unreal = @{Locations = @("C:\Program Files\Epic Games")}
    OBS = @{Locations = @("C:\Program Files\obs-studio", "$env:APPDATA\obs-studio")}
    Git = @{Locations = @("$env:ProgramFiles\Git")}
    Docker = @{Locations = @("$env:ProgramFiles\Docker")}
}

$DevToolStatus = foreach ($tool in $DevTools.GetEnumerator()) {
    $found = $false
    $locations = @()
    foreach ($loc in $tool.Value.Locations) {
        # Handle wildcards
        if ($loc -like "**") {
            $matches = Get-ChildItem -Path (Split-Path $loc) -Filter (Split-Path -Leaf $loc) -Directory -ErrorAction SilentlyContinue
            if ($matches) {
                $locations += $matches.FullName
                $found = $true
            }
        } elseif (Test-Path $loc) {
            $locations += $loc
            $found = $true
        }
    }
    [PSCustomObject]@{
        Tool = $tool.Key
        Found = $found
        Locations = $locations -join "; "
        EnvVar = $tool.Value.EnvVar
    }
}

$DevToolStatus | Export-Csv "$BackupDir\dev_tools_status.csv" -NoTypeInformation
Write-Host "  Development tools status exported to dev_tools_status.csv"

Write-Host ""

# Section E: Drive Space Analysis
Write-Host "Section E: Analyzing drive space..."

try {
    Get-WmiObject Win32_LogicalDisk | Select-Object DeviceID, VolumeName, 
        @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}, 
        @{N='FreeGB';E={[math]::Round($_.FreeSpace/1GB,2)}} | 
        Format-Table -AutoSize | Out-String | Out-File "$BackupDir\drive_space.txt"
    Write-Host "  Drive space analysis exported to drive_space.txt"
} catch {
    Write-Warning "  Could not analyze drive space: $_"
}

Write-Host ""

# Section F: Output File Manifest
Write-Host "Section F: Creating manifest..."

$manifest = @{
    BackupTimestamp = $timestamp
    BackupDirectory = $BackupDir
    Sections = @(
        @{ Name = "Installed Programs"; File = "installed_programs.csv" }
        @{ Name = "VS Code Extensions"; File = "vscode_extensions.txt" }
        @{ Name = "NPM Global Packages"; File = "npm_global.json" }
        @{ Name = "PIP Packages"; File = "pip_packages.txt" }
        @{ Name = "Cargo Packages"; File = "cargo_packages.txt" }
        @{ Name = "DotNet Tools"; File = "dotnet_tools.txt" }
        @{ Name = "WSL Distros"; File = "wsl_distros.txt" }
        @{ Name = "VST Paths Found"; File = "VST_paths_found.txt" }
        @{ Name = "Ableton Paths Found"; File = "Ableton_paths_found.txt" }
        @{ Name = "Ableton Registry"; File = "Ableton_registry.txt" }
        @{ Name = "Development Tools Status"; File = "dev_tools_status.csv" }
        @{ Name = "Drive Space Analysis"; File = "drive_space.txt" }
    )
    VSTPathsChecked = $VSTPaths
    AbletonPathsChecked = $AbletonPaths
}

$manifest | ConvertTo-Json -Depth 4 | Out-File "$BackupDir\MANIFEST.json" -Encoding UTF8
Write-Host "  Manifest created as MANIFEST.json"

Write-Host ""
Write-Host "=== Inventory Complete ==="
Write-Host "All data saved to: $BackupDir"
Write-Host "Next steps:"
Write-Host "  1. Verify the backup directory contains all expected files"
Write-Host "  2. Copy the backup directory to external storage"
Write-Host "  3. Proceed with Windows 11 installation"