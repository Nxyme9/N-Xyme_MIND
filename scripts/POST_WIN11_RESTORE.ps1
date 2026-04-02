# POST_WIN11_RESTORE.ps1
# Script to restore data after Windows 11 fresh installation
# Author: N-Xyme
# Created: $(Get-Date -Format 'yyyy-MM-dd')

Write-Host "=== Windows 11 Post-Install Restore ==="
Write-Host "This script helps restore your data after a clean Windows 11 install"
Write-Host ""

# Section A: Check Environment
Write-Host "Section A: Checking environment and Macrium image locations..."

# Detect if running from WinPE, Macrium rescue, or installed Windows
$isWinPE = $false
if ([Environment]::OSVersion.Version.Build -lt 10000) {
    $isWinPE = $true
    Write-Host "  Detected: Running in Windows PE (WinPE) environment"
} else {
    Write-Host "  Detected: Running in installed Windows"
}

# Check if Macrium image exists at known locations
$ImagePaths = @(
    "D:\Macrium\*",
    "D:\*Macrium*",
    "E:\Macrium\*",
    "E:\*Image*",
    "$env:USERPROFILE\Documents\Macrium\*"
)

$foundImages = @()
foreach ($pathPattern in $ImagePaths) {
    $resolvedPath = $pathPattern -replace '\*', ''
    if (Test-Path $resolvedPath) {
        $images = Get-ChildItem -Path $resolvedPath -Filter "*.mrimg" -ErrorAction SilentlyContinue
        if ($images) {
            $foundImages += $images
        }
    }
}

if ($foundImages.Count -gt 0) {
    Write-Host "  Found $($foundImages.Count) Macrium image(s):"
    foreach ($img in $foundImages) {
        Write-Host "    $($img.FullName)"
    }
    $ImageAvailable = $true
} else {
    Write-Warning "  No Macrium images found in common locations"
    $ImageAvailable = $false
}

Write-Host ""

# Section B: Try Image Mount (with fallback)
Write-Host "Section B: Attempting to mount Macrium image..."

function Mount-MacriumImage {
    param([string]$ImagePath, [string]$MountLetter = "X")
    
    # Try Macrium CLI first
    $macriumExe = "C:\Program Files\Macrium\Reflect\Reflect.exe"
    if (Test-Path $macriumExe) {
        Write-Host "  Attempting to mount image using Macrium Reflect CLI..."
        try {
            # Note: Actual Macrium CLI syntax may vary - this is a placeholder
            # & $macriumExe --mount --file "$ImagePath" --letter $MountLetter
            Write-Host "  Macrium Reflect found at: $macriumExe"
            Write-Host "  NOTE: Actual mounting requires Macrium Reflect GUI or WinPE environment"
            Write-Warning "  Automatic mounting via CLI not fully implemented - please use Macrium Reflect GUI"
            return $false
        } catch {
            Write-Warning "  Macrium CLI mount failed: $_"
        }
    } else {
        Write-Warning "  Macrium Reflect not found at expected location: $macriumExe"
    }
    
    # Try 7-zip as fallback (some Macrium formats are mountable)
    $7z = "C:\Program Files\7-Zip\7z.exe"
    if (Test-Path $7z) {
        Write-Host "  7-Zip found at: $7z"
        Write-Warning "  7-zip cannot mount Macrium (.mrimg) images natively"
    } else {
        Write-Warning "  7-Zip not found"
    }
    
    # Fallback: guide user to mount manually
    Write-Host ""
    Write-Host "=== MANUAL IMAGE MOUNT REQUIRED ==="
    Write-Host "Please follow these steps:"
    Write-Host "1. Open Macrium Reflect"
    Write-Host "2. Browse to your backup image (.mrimg file)"
    Write-Host "3. Right-click the image and select 'Mount Image'"
    Write-Host "4. Assign a drive letter (e.g., X:)"
    Write-Host "5. Note the drive letter assigned"
    Write-Host "6. Run this script again, specifying the mounted drive letter"
    Write-Host ""
    
    $mountedLetter = Read-Host "Enter the drive letter of the mounted image (e.g., X) or press Enter to skip"
    if ($mountedLetter) {
        return $mountedLetter.ToUpper()
    } else {
        return $null
    }
}

$mountedDrive = $null
if ($ImageAvailable) {
    # Use first found image
    $firstImage = $foundImages[0].FullName
    Write-Host "Using image: $firstImage"
    $mountedDrive = Mount-MacriumImage -ImagePath $firstImage
    
    if ($mountedDrive) {
        $ImageMounted = $true
        Write-Host "Proceeding with mounted drive: $mountedDrive`:"
    } else {
        $ImageMounted = $false
        Write-Warning "No drive mounted - will provide manual copy instructions"
    }
} else {
    $ImageMounted = $false
    Write-Warning "No image available to mount"
}

Write-Host ""

# Section C: Selective Restore from Image
if ($ImageMounted) {
    Write-Host "Section C: Restoring from mounted image ($mountedDrive`:)"
    
    # Define restore operations
    $restoreOperations = @()
    
    # Step 1: User Configs (runs first, fastest)
    $UserConfigs = @(
        @{Source="$mountedDrive`:\Users\N-Xyme\.config"; Dest="$env:USERPROFILE\.config"; Desc="All user configs (OpenCode, etc.)"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.vscode"; Dest="$env:USERPROFILE\.vscode"; Desc="VS Code settings + extensions"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.claude"; Dest="$env:USERPROFILE\.claude"; Desc="Claude config"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.continue"; Dest="$env:USERPROFILE\.continue"; Desc="Continue config"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.codex"; Dest="$env:USERPROFILE\.codex"; Desc="Codex config"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.afirma"; Dest="$env:USERPROFILE\.afirma"; Desc="Afirma config"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.ollama"; Dest="$env:USERPROFILE\.ollama"; Desc="Ollama config"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.openclaw"; Dest="$env:USERPROFILE\.openclaw"; Desc="OpenClaw config"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.serena"; Dest="$env:USERPROFILE\.serena"; Desc="Serena config"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.cagent"; Dest="$env:USERPROFILE\.cagent"; Desc="Cagent config"; Required=$false}
    )
    
    # Step 2: Development Environments
    $DevRestore = @(
        @{Source="$mountedDrive`:\Users\N-Xyme\.cargo"; Dest="$env:USERPROFILE\.cargo"; Desc="Rust/Cargo"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\go"; Dest="$env:USERPROFILE\go"; Desc="Go packages"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.gradle"; Dest="$env:USERPROFILE\.gradle"; Desc="Gradle"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.m2"; Dest="$env:USERPROFILE\.m2"; Desc="Maven"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\AppData\Local\npm"; Dest="$env:LOCALAPPDATA\npm"; Desc="npm global packages"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\AppData\Roaming\npm"; Dest="$env:APPDATA\npm"; Desc="npm config"; Required=$false}
    )
    
    # Step 3: Ableton + Music Production
    $AbletonRestore = @(
        @{Source="$mountedDrive`:\Users\N-Xyme\Documents\Ableton"; Dest="$env:USERPROFILE\Documents\Ableton"; Desc="Ableton Projects + Library"; Required=$true},
        @{Source="$mountedDrive`:\ProgramData\Ableton"; Dest="C:\ProgramData\Ableton"; Desc="Ableton Program Data"; Required=$true},
        @{Source="$mountedDrive`:\Program Files (x86)\Steinberg"; Dest="C:\Program Files (x86)\Steinberg"; Desc="Steinberg VSTs"; Required=$false},
        @{Source="$mountedDrive`:\Program Files\Steinberg"; Dest="C:\Program Files\Steinberg"; Desc="Steinberg VSTs"; Required=$false},
        @{Source="$mountedDrive`:\Program Files (x86)\VSTPlugins"; Dest="C:\Program Files (x86)\VSTPlugins"; Desc="32-bit VSTs"; Required=$false},
        @{Source="$mountedDrive`:\Program Files\VSTPlugins"; Dest="C:\Program Files\VSTPlugins"; Desc="64-bit VSTs"; Required=$false},
        @{Source="$mountedDrive`:\Program Files\Common Files\VST3"; Dest="C:\Program Files\Common Files\VST3"; Desc="VST3 Plugins"; Required=$false},
        @{Source="$mountedDrive`:\Program Files\Common Files\Steinberg"; Dest="C:\Program Files\Common Files\Steinberg"; Desc="Steinberg Common"; Required=$false},
        @{Source="$mountedDrive`:\Program Files\Native Instruments"; Dest="C:\Program Files\Native Instruments"; Desc="Native Instruments"; Required=$false},
        @{Source="$mountedDrive`:\Program Files\FL Studio"; Dest="C:\Program Files\FL Studio"; Desc="FL Studio"; Required=$false},
        @{Source="$mountedDrive`:\Program Files\Reaper"; Dest="C:\Program Files\Reaper"; Desc="REAPER"; Required=$false},
        @{Source="$mountedDrive`:\Program Files\Image-Line"; Dest="C:\Program Files\Image-Line"; Desc="Image-Line"; Required=$false},
        @{Source="$mountedDrive`:\ProgramData\PluginAlliance"; Dest="C:\ProgramData\PluginAlliance"; Desc="Plugin Alliance"; Required=$false},
        @{Source="$mountedDrive`:\ProgramData\UVI"; Dest="C:\ProgramData\UVI"; Desc="UVI"; Required=$false},
        @{Source="$mountedDrive`:\ProgramData\iZotope"; Dest="C:\ProgramData\iZotope"; Desc="iZotope"; Required=$false},
        @{Source="$mountedDrive`:\ProgramData\FabFilter"; Dest="C:\ProgramData\FabFilter"; Desc="FabFilter"; Required=$false}
    )
    
    # Step 4: Visual Studio + JetBrains
    $IDE_Restore = @(
        @{Source="$mountedDrive`:\Users\N-Xyme\AppData\Local\JetBrains"; Dest="$env:LOCALAPPDATA\JetBrains"; Desc="JetBrains IDEs"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\AppData\Roaming\JetBrains"; Dest="$env:APPDATA\JetBrains"; Desc="JetBrains Settings"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.android"; Dest="$env:USERPROFILE\.android"; Desc="Android SDK config"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\AppData\Local\Android"; Dest="$env:LOCALAPPDATA\Android"; Desc="Android SDK"; Required=$false}
    )
    
    # Step 5: Docker + Ollama Data
    $DataRestore = @(
        @{Source="$mountedDrive`:\Users\N-Xyme\.docker"; Dest="$env:USERPROFILE\.docker"; Desc="Docker config"; Required=$false},
        @{Source="$mountedDrive`:\ProgramData\docker"; Dest="$env:ProgramData\docker"; Desc="Docker ProgramData"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\AppData\Local\Docker"; Dest="$env:LOCALAPPDATA\Docker"; Desc="Docker LocalData"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\.wslDistributions.json"; Dest="$env:USERPROFILE\.wslDistributions.json"; Desc="WSL Config"; Required=$false}
    )
    
    # Step 6: Games + Misc
    $GamesRestore = @(
        @{Source="$mountedDrive`:\Program Files\Epic Games"; Dest="C:\Program Files\Epic Games"; Desc="Epic Games"; Required=$false},
        @{Source="$mountedDrive`:\Program Files (x86)\Steam"; Dest="C:\Program Files (x86)\Steam"; Desc="Steam"; Required=$false},
        @{Source="$mountedDrive`:\Program Files\Steam"; Dest="C:\Program Files\Steam"; Desc="Steam (alt)"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\AppData\Local\OBS"; Dest="$env:LOCALAPPDATA\OBS"; Desc="OBS Studio"; Required=$false},
        @{Source="$mountedDrive`:\Users\N-Xyme\AppData\Roaming\obs-studio"; Dest="$env:APPDATA\obs-studio"; Desc="OBS Config"; Required=$false}
    )
    
    # Combine all restore operations
    $allOperations = $UserConfigs + $DevRestore + $AbletonRestore + $IDE_Restore + $DataRestore + $GamesRestore
    
    Write-Host "Starting restore process..."
    Write-Host "Total operations to perform: $($allOperations.Count)"
    
    $successCount = 0
    $skipCount = 0
    $errorCount = 0
    
    foreach ($op in $allOperations) {
        if (Test-Path $op.Source) {
            try {
                # Ensure destination directory exists
                $destDir = Split-Path $op.Dest -Parent
                if (-not (Test-Path $destDir)) {
                    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
                }
                
                # Copy files
                if (Test-Path "$op.Source\*") {
                    # Use safe copy without deletion semantics (avoid /MIR as required)
                    robocopy $op.Source $op.Dest /E /COPYALL /R:2 /W:5 /NFL /NDL /NP > $null
                    Write-Host "  [OK] $op.Desc"
                    $successCount++
                } else {
                    Write-Host "  [SKIP] $op.Desc (source empty)"
                    $skipCount++
                }
            } catch {
                Write-Warning "  [ERROR] $op.Desc: $_"
                $errorCount++
            }
        } elseif ($op.Required) {
            Write-Warning "  [MISSING REQUIRED] $op.Desc"
            Write-Warning "      Source not found: $op.Source"
            $errorCount++
        } else {
            Write-Host "  [SKIP] $op.Desc (source not found)"
            $skipCount++
        }
    }
    
    Write-Host ""
    Write-Host "=== Restore Summary ==="
    Write-Host "  Successful: $successCount"
    Write-Host "  Skipped: $skipCount"
    Write-Host "  Errors: $errorCount"
    
} else {
    Write-Host "Section C: Skipping automatic restore (no image mounted)"
    Write-Host "Please follow the manual restore instructions below:"
    Write-Host ""
}

Write-Host ""

# Section D: Registry Restore (User Hive Only - SAFE)
Write-Host "Section D: Registry Restore Guidance"
Write-Host ""
Write-Host "To restore registry settings (USER hive only - SAFE):"
Write-Host "1. Boot into Macrium WinPE rescue environment"
Write-Host "2. Open Macrium Reflect"
Write-Host "3. Select 'Restore' -> 'Browse for an image or backup'"
Write-Host "4. Navigate to your .mrimg file"
Write-Host "5. During restore, choose 'Advanced options'"
Write-Host "6. Under 'What to restore', select ONLY:"
Write-Host "    - Users\N-Xyme\NTUSER.DAT (this is HKCU)"
Write-Host "7. DO NOT restore Windows system files or HKLM"
Write-Host "8. Complete the restore process"
Write-Host ""
Write-Host "WARNING: Never restore HKLM from a different Windows installation!"
Write-Host ""

# Section E: Package Reinstall Generator
Write-Host "Section E: Generating package reinstall scripts..."

if (Test-Path "$env:USERPROFILE\Documents\Win11_prepare_*\MANIFEST.json") {
    # Find latest backup
    $latestBackup = Get-ChildItem -Path "$env:USERPROFILE\Documents\Win11_prepare_*" -Directory | Sort-Object CreationTime -Descending | Select-Object -First 1
    if ($latestBackup) {
        $BackupDir = $latestBackup.FullName
        Write-Host "Using backup directory: $BackupDir"
        
        # Generate RESTORE_PACKAGES.bat
        $restoreBat = @"
@echo OFF
echo ========================================
echo N-XYME PACKAGE RESTORE SCRIPT
echo Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm')
echo ========================================
echo.

REM --- npm global packages ---
if exist "$BackupDir\npm_global.json" (
    echo Installing npm global packages...
    for /f "skip=2 tokens=*" %%A in ('type "%BackupDir%\npm_global.json" ^| findstr /r /v "^[{} ]*$" ^| findstr /i """%%A"""') do (
        for /f "tokens=2 delims=:" %%B in (%%A) do (
            set "pkg=%%B"
            set "pkg=!pkg:"=!"
            set "pkg=!pkg:,=!"
            if not "!pkg!"=="" (
                echo   Installing !pkg!
                npm install -g !pkg!
            )
        )
    )
) else (
    echo WARNING: npm_global.json not found - skipping npm restore
)

echo.
REM --- pip packages ---
if exist "$BackupDir\pip_packages.txt" (
    echo Installing Python packages...
    pip install -r "%BackupDir%\pip_packages.txt"
) else (
    echo WARNING: pip_packages.txt not found - skipping pip restore
)

echo.
REM --- VS Code Extensions ---
if exist "$BackupDir\vscode_extensions.txt" (
    echo Installing VS Code Extensions...
    for /f "usebackq" %%E in ("%BackupDir%\vscode_extensions.txt") do (
        if not "%%E"=="" (
            echo   Installing %%E
            code --install-extension %%E
        )
    )
) else (
    echo WARNING: vscode_extensions.txt not found - skipping VS Code extensions
)

echo.
echo ========================================
echo PACKAGE RESTORE COMPLETE
echo ========================================
"@
        
        $restoreBat | Out-File "$env:USERPROFILE\Desktop\RESTORE_PACKAGES.bat" -Encoding ASCII
        Write-Host "  Package restore script saved to: $env:USERPROFILE\Desktop\RESTORE_PACKAGES.bat"
        
        # Generate VS Code extension reinstall script
        if (Test-Path "$BackupDir\vscode_extensions.txt") {
            $extensions = Get-Content "$BackupDir\vscode_extensions.txt"
            $installScript = $extensions | ForEach-Object { "code --install-extension $_" }
            $installScript | Out-File "$env:USERPROFILE\Desktop\RESTORE_VSCODE.bat" -Encoding UTF8
            Write-Host "  VS Code extension restore script saved to: $env:USERPROFILE\Desktop\RESTORE_VSCODE.bat"
        }
    } else {
        Write-Warning "  Could not find backup directory for package restore generation"
    }
} else {
    Write-Warning "  No pre-upgrade backup found - skipping package restore script generation"
}

Write-Host ""

# Section F: Macrium Image Mount Instructions (if auto-mount fails)
if (-not $ImageMounted) {
    Write-Host "Section F: Manual Macrium Image Mount Instructions"
    Write-Host ""
    Write-Host "If you need to mount the Macrium image manually:"
    Write-Host ""
    Write-Host "Method 1: Using Macrium Reflect (Windows)"
    Write-Host "  1. Open Macrium Reflect"
    Write-Host "  2. Click the 'Backup' tab if not already selected"
    Write-Host "  3. Locate your backup set in the center pane"
    Write-Host "  4. Right-click the backup set and choose 'Explore Image'"
    Write-Host "  5. Select the partition to explore (usually the largest one)"
    Write-Host "  6. Assign a drive letter when prompted"
    Write-Host "  7. Click OK to mount the image"
    Write-Host ""
    Write-Host "Method 2: Using Macrium WinPE"
    Write-Host "  1. Create Macrium WinPE rescue media (if you don't have it)"
    Write-Host "  2. Boot from the WinPE media"
    Write-Host "  3. In Macrium Reflect, select the image to mount"
    Write-Host "  4. Choose 'Mount Image' and assign a drive letter"
    Write-Host ""
    Write-Host "Once mounted, note the drive letter and copy files manually from that drive."
    Write-Host ""
}

# Section G: Post-Restore Checklist
Write-Host "Section G: Post-Restore Checklist"
Write-Host ""
Write-Host "After completing the restore, please verify:"
Write-Host "  [ ] Docker Desktop starts correctly"
Write-Host "  [ ] Ollama responds (run 'ollama list')"
Write-Host "  [ ] Neo4j accessible (if installed)"
Write-Host "  [ ] VS Code opens with all extensions"
Write-Host "  [ ] Ableton launches and detects VSTs"
Write-Host "  [ ] WSL distributions are accessible (wsl --list)"
Write-Host "  [ ] Development tools work (npm, pip, cargo, dotnet, go, rust)"
Write-Host ""
Write-Host "=== Restore Process Complete ==="
Write-Host "Please review any warnings or errors above."
Write-Host "Manual steps may be required for certain components."
