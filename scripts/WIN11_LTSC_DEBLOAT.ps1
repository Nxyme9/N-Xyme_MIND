param([switch]$SkipAudio, [switch]$SkipNetwork, [switch]$SkipSpectre, [switch]$WhatIf)

# Debloat script for Windows 11 LTSC - Win11_LTSC_DEBLOAT.ps1
# Sections implemented as requested, with admin guard and restore point creation.

$ErrorActionPreference = 'Stop'

$logPath = "D:\01_CODING\00_N-Xyme_CATALYST\scripts\WIN11_LTSC_DEBLOAT.log"
function Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts`t$Message" | Out-File -FilePath $logPath -Append -Encoding utf8
}

Log "Starting WIN11_LTSC_DEBLOAT.ps1"

## 1) Admin check
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Administrator privileges are required. Run this script as Administrator."
    Log "ERROR: Not running as Administrator"
    exit 1
}
Log "Administrator check passed"

## 1) System restore point
Log "Section 1: Creating system restore point (Checkpoint-Computer)"
$cpParams = @{ Description = "WIN11_LTSC_DEBLOAT"; RestorePointType = 'MODIFY_SETTINGS' }
if ($WhatIf) { Checkpoint-Computer -Description $cpParams.Description -RestorePointType $cpParams.RestorePointType -WhatIf } else { Checkpoint-Computer -Description $cpParams.Description -RestorePointType $cpParams.RestorePointType }

## 2) Disable services
Log "Section 2: Disable specified services"
$servicesToDisable = @("DiagTrack","dmwappushservice","WMPNetworkSvc","MapsBroker","lfsvc","RetailDemo","RemoteRegistry","TabletInputService","SysMain","Spooler","PrintNotify","WpnService","WerSvc","MicrosoftEdgeElevationService","edgeupdate","edgeupdatem","dmwapushservice","DusmSvc","autotimesvc","DeviceAssociationService")
foreach ($svc in $servicesToDisable) {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if (-not $s) {
        Log "Service not found (skipped): $svc"
        continue
    }
    if ($WhatIf) {
        Log "WhatIf: would stop and disable service $svc"
        continue
    }
    try {
        if ($s.Status -eq 'Running') { Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue }
        Set-Service -Name $svc -StartupType Disabled -ErrorAction SilentlyContinue
        Log "Service $svc stopped and disabled"
    } catch { Log "ERROR disabling service $svc: $_" }
}

## 3) Telemetry (registry) - All changes are precautionary and per-request
Log "Section 3: Telemetry/Privacy settings (registry)"
try {
    $paths = @(
        @("HKLM:\Software\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0),
        @("HKLM:\Software\Policies\Microsoft\Windows\DataCollection", "ConsentTelemetry", 0),
        @("HKLM:\Software\Policies\Microsoft\Windows\AdvertisingInfo", "DoNotTrack", 1)
    )
    # Ensure base path exists for AllowTelemetry/ConsentTelemetry
    $telePath = "HKLM:\Software\Policies\Microsoft\Windows\DataCollection"
    if (-not (Test-Path $telePath)) { New-Item -Path $telePath -Force | Out-Null }
    New-ItemProperty -Path $telePath -Name "AllowTelemetry" -PropertyType DWord -Value 0 -Force | Out-Null
    New-ItemProperty -Path $telePath -Name "ConsentTelemetry" -PropertyType DWord -Value 0 -Force | Out-Null
    # Advertising ID (per-user)
    $advPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo"
    if (-not (Test-Path $advPath)) { New-Item -Path $advPath -Force | Out-Null }
    New-ItemProperty -Path $advPath -Name "Enabled" -PropertyType DWord -Value 0 -Force | Out-Null
    # Location privacy
    $locPath = "HKLM:\Software\Policies\Microsoft\Windows\LocationAndPrivacy"
    if (-not (Test-Path $locPath)) { New-Item -Path $locPath -Force | Out-Null }
    New-ItemProperty -Path $locPath -Name "Value" -PropertyType DWord -Value 0 -Force | Out-Null
    # Activity history and speech privacy (best-effort entries)
    $actPath = "HKLM:\Software\Policies\Microsoft\Windows\Settings"
    if (-not (Test-Path $actPath)) { New-Item -Path $actPath -Force | Out-Null }
    New-ItemProperty -Path $actPath -Name "DoNotStoreActivityHistory" -PropertyType DWord -Value 1 -Force | Out-Null
    $speechPath = "HKLM:\Software\Policies\Microsoft\Windows\Speech"
    if (-not (Test-Path $speechPath)) { New-Item -Path $speechPath -Force | Out-Null }
    New-ItemProperty -Path $speechPath -Name "DisableSpeech" -PropertyType DWord -Value 1 -Force | Out-Null
    Log "Telemetry registry keys set (may depend on LTSC specifics)."
} catch {
    Log "ERROR setting telemetry keys: $_"
}

## 4) Performance / CPU/Gaming related tweaks
Log "Section 4: Performance optimizations for LTSC 7800X3D"
try {
    # 4A. Disable CPU power throttling (PowerThrottling)
    $pthPath = "HKLM:\Software\Policies\Microsoft\Windows\Power"
    if (-not (Test-Path $pthPath)) { New-Item -Path $pthPath -Force | Out-Null }
    New-ItemProperty -Path $pthPath -Name "PowerThrottlingOff" -PropertyType DWord -Value 1 -Force | Out-Null

    # 4B. Set High Performance plan
    $highPerfGuid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
    if ($WhatIf) { Log "WhatIf: would set active power scheme to High Performance ($highPerfGuid)" } else { powercfg -setactive $highPerfGuid }

    # 4C. Disable Game Bar & Game Mode & fullscreen optimizations
    $gameDVRPath = "HKLM:\Software\Policies\Microsoft\Windows\GameDVR"
    if (-not (Test-Path $gameDVRPath)) { New-Item -Path $gameDVRPath -Force | Out-Null }
    New-ItemProperty -Path $gameDVRPath -Name "AllowGameDVR" -PropertyType DWord -Value 0 -Force | Out-Null

    $gmPath = "HKLM:\Software\Policies\Microsoft\WindowsGameMode"
    if (-not (Test-Path $gmPath)) { New-Item -Path $gmPath -Force | Out-Null }
    New-ItemProperty -Path $gmPath -Name "DisableGameMode" -PropertyType DWord -Value 1 -Force | Out-Null

    $fsPath = "HKLM:\Software\Microsoft\Avalon.Graphics"
    if (-not (Test-Path $fsPath)) { New-Item -Path $fsPath -Force | Out-Null }
    New-ItemProperty -Path $fsPath -Name "DisableFullscreenOptimizations" -PropertyType DWord -Value 1 -Force | Out-Null

    # 4D. HPET platform clock (disable via bcdedit)
    if ($WhatIf) { Log "WhatIf: would run 'bcdedit /set useplatformclock true'" } else { & bcdedit /set useplatformclock true | Out-Null }
} catch { Log "ERROR in Section 4: $($_.Exception.Message)" }

## 5) Network / Gaming related settings
Log "Section 5: Network/Gaming performance tweaks (best-effort)"
try {
    $tcpPath = "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
    if (-not (Test-Path $tcpPath)) { New-Item -Path $tcpPath -Force | Out-Null }
    New-ItemProperty -Path $tcpPath -Name "TcpAckFrequency" -PropertyType DWord -Value 1 -Force | Out-Null
    New-ItemProperty -Path $tcpPath -Name "TCPNoDelay" -PropertyType DWord -Value 1 -Force | Out-Null
    New-ItemProperty -Path $tcpPath -Name "ECN" -PropertyType DWord -Value 0 -Force | Out-Null

    # System responsiveness and gaming profile (best-effort)
    $sysResPath = "HKLM:\Software\Policies\Microsoft\Windows\CurrentVersion\GameDVR"
    if (-not (Test-Path $sysResPath)) { New-Item -Path $sysResPath -Force | Out-Null }
    New-ItemProperty -Path $sysResPath -Name "SystemResponsiveness" -PropertyType DWord -Value 0 -Force | Out-Null

    $gpuPath = "HKLM:\Software\Policies\Microsoft\Windows\Gaming"
    if (-not (Test-Path $gpuPath)) { New-Item -Path $gpuPath -Force | Out-Null }
    New-ItemProperty -Path $gpuPath -Name "GPUPriority" -PropertyType DWord -Value 8 -Force | Out-Null
    New-ItemProperty -Path $gpuPath -Name "Priority" -PropertyType DWord -Value 6 -Force | Out-Null
    New-ItemProperty -Path $gpuPath -Name "SchedulingCategory" -PropertyType DWord -Value 5 -Force | Out-Null
    New-ItemProperty -Path $gpuPath -Name "SFIOPriority" -PropertyType DWord -Value 2 -Force | Out-Null
    New-ItemProperty -Path $gpuPath -Name "LatencySensitive" -PropertyType DWord -Value 1 -Force | Out-Null
} catch { Log "ERROR in Section 5: $($_.Exception.Message)" }

## 6) Audio tweaks
Log "Section 6: Audio optimizations"
try {
    if ($SkipAudio) { Log "Audio tweaks skipped via parameter" }
    else {
        # Disable system sound ducking (0=mute others, 1=reduce80%, 2=reduce50%, 3=no reduction)
        $aPath = "HKCU:\Software\Microsoft\Multimedia\Audio"
        if (-not (Test-Path $aPath)) { New-Item -Path $aPath -Force | Out-Null }
        New-ItemProperty -Path $aPath -Name "UserDuckingPreference" -PropertyType DWord -Value 3 -Force | Out-Null
        # Registry policy: disable audio enhancements globally
        $polPath = "HKLM:\Software\Policies\Microsoft\Windows\Audio"
        if (-not (Test-Path $polPath)) { New-Item -Path $polPath -Force | Out-Null }
        New-ItemProperty -Path $polPath -Name "DisableAudioEnhancements" -PropertyType DWord -Value 1 -Force | Out-Null
        # Disable per-device audio enhancements (renders and captures)
        $renderPath = "HKCU:\Software\Microsoft\Internet Explorer\LowRegistry\Audio\PolicyConfig\PropertyStore"
        $capturePath = "HKCU:\Software\Microsoft\Internet Explorer\LowRegistry\Audio\PolicyConfig\PropertyStore"
        foreach ($p in @($renderPath)) {
            if (Test-Path $p) {
                Get-ChildItem $p -ErrorAction SilentlyContinue | ForEach-Object {
                    try {
                        Set-ItemProperty -Path $_.PSPath -Name "fx_DisableEnhancements" -Value 1 -ErrorAction SilentlyContinue
                        Log "Audio enhancements disabled: $($_.PSChildName)"
                    } catch {}
                }
            }
        }
        Log "Audio tweaks applied"
    }
} catch { Log "ERROR in Section 6: $($_.Exception.Message)" }

## 7) Visual tweaks
Log "Section 7: Visual/UI tweaks"
try {
    $personalizePath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    if (-not (Test-Path $personalizePath)) { New-Item -Path $personalizePath -Force | Out-Null }
    New-ItemProperty -Path $personalizePath -Name "EnableTransparency" -PropertyType DWord -Value 0 -Force | Out-Null

    $desktopPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    if (-not (Test-Path $desktopPath)) { New-Item -Path $desktopPath -Force | Out-Null }
    New-ItemProperty -Path $desktopPath -Name "MenuShowDelay" -PropertyType DWord -Value 0 -Force | Out-Null
    New-ItemProperty -Path $desktopPath -Name "Animation" -PropertyType DWord -Value 0 -Force | Out-Null
    New-ItemProperty -Path $desktopPath -Name "SmoothScrollInitialized" -PropertyType DWord -Value 0 -Force | Out-Null
} catch { Log "ERROR in Section 7: $($_.Exception.Message)" }

## 8) Explorer tweaks
Log "Section 8: Explorer-related tweaks"
try {
    $advPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    if (-not (Test-Path $advPath)) { New-Item -Path $advPath -Force | Out-Null }
    # Show file extensions and hidden items
    New-ItemProperty -Path $advPath -Name "HideFileExt" -PropertyType DWord -Value 0 -Force | Out-Null
    New-ItemProperty -Path $advPath -Name "Hidden" -PropertyType DWord -Value 1 -Force | Out-Null
    # Disable Quick Access (set Explorer to open This PC)
    New-ItemProperty -Path $advPath -Name "LaunchTo" -PropertyType DWord -Value 1 -Force | Out-Null
    # Disable Bing search in Explorer search box
    $bingPath = "HKLM:\Software\Policies\Microsoft\Windows\Explorer"
    if (-not (Test-Path $bingPath)) { New-Item -Path $bingPath -Force | Out-Null }
    New-ItemProperty -Path $bingPath -Name "DisableSearchBoxSuggestions" -PropertyType DWord -Value 1 -Force | Out-Null
    # Disable search suggestions (Cortana/Edge)
    $searchPath = "HKCU:\Software\Policies\Microsoft\Windows\Explorer"
    if (-not (Test-Path $searchPath)) { New-Item -Path $searchPath -Force | Out-Null }
    New-ItemProperty -Path $searchPath -Name "DisableSearchBoxSuggestions" -PropertyType DWord -Value 1 -Force | Out-Null
    # Classic context menu (Windows 11)
    $cmPath = "HKCU:\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32"
    if (-not (Test-Path $cmPath)) { New-Item -Path $cmPath -Force | Out-Null }
    Set-ItemProperty -Path $cmPath -Name "(Default)" -Value "" -Force
    # Disable Sticky Keys
    $stickyPath = "HKCU:\Control Panel\Accessibility\StickyKeys"
    if (-not (Test-Path $stickyPath)) { New-Item -Path $stickyPath -Force | Out-Null }
    New-ItemProperty -Path $stickyPath -Name "Flags" -PropertyType String -Value "506" -Force | Out-Null
    # Disable Filter Keys
    $filterPath = "HKCU:\Control Panel\Accessibility\Keyboard Response"
    if (-not (Test-Path $filterPath)) { New-Item -Path $filterPath -Force | Out-Null }
    New-ItemProperty -Path $filterPath -Name "Flags" -PropertyType String -Value "122" -Force | Out-Null
    # Disable Toggle Keys
    $togglePath = "HKCU:\Control Panel\Accessibility\ToggleKeys"
    if (-not (Test-Path $togglePath)) { New-Item -Path $togglePath -Force | Out-Null }
    New-ItemProperty -Path $togglePath -Name "Flags" -PropertyType String -Value "58" -Force | Out-Null
    # Disable mouse acceleration (Enhance pointer precision)
    $mousePath = "HKCU:\Control Panel\Mouse"
    if (-not (Test-Path $mousePath)) { New-Item -Path $mousePath -Force | Out-Null }
    New-ItemProperty -Path $mousePath -Name "MouseSpeed" -PropertyType String -Value "0" -Force | Out-Null
    New-ItemProperty -Path $mousePath -Name "MouseThreshold1" -PropertyType String -Value "0" -Force | Out-Null
    New-ItemProperty -Path $mousePath -Name "MouseThreshold2" -PropertyType String -Value "0" -Force | Out-Null
    Log "Explorer tweaks applied"
} catch { Log "ERROR in Section 8: $($_.Exception.Message)" }

## 9) Memory / File System tweaks
Log "Section 9: Memory / File System tweaks"
try {
    # Last access time tracking
    fsutil behavior set disablelastaccess 1
    # 8.3 name creation
    fsutil behavior set disable8dot3 1
    # Hibernation and Fast Startup
    powercfg /hibernate off
} catch { Log "ERROR in Section 9: $($_.Exception.Message)" }

## 10) NVIDIA telemetry container
Log "Section 10: NVIDIA telemetry container (best-effort)"
try {
    $svcNvidia = "NvTelemetryContainer"
    $svc = Get-Service -Name $svcNvidia -ErrorAction SilentlyContinue
    if ($svc) {
        if ($WhatIf) { Log "WhatIf: would stop/disable $svcNvidia" } else {
            Stop-Service -Name $svcNvidia -Force -ErrorAction SilentlyContinue
            Set-Service -Name $svcNvidia -StartupType Disabled -ErrorAction SilentlyContinue
        }
    } else {
        Log "NVIDIA telemetry service not found; skipping."
    }
} catch { Log "ERROR in Section 10: $($_.Exception.Message)" }

## 11) Summary report
Log "Section 11: Summary and verification"
Write-Host "`n========================================"
Write-Host " WIN11_LTSC_DEBLOAT - SUMMARY REPORT"
Write-Host "========================================`n"

$nvidiaSvc = Get-Service -Name "NvTelemetryContainer" -EA SilentlyContinue
$nvidiaStatus = if ($nvidiaSvc) {
    if ($nvidiaSvc.StartType -eq 'Disabled') { "Disabled" } else { "Active" }
} else { "Not found" }

$report = [ordered]@{
    "System Restore"      = if ($WhatIf) { "Skipped (WhatIf)" } else { "Created" }
    "Services Disabled"   = ($servicesToDisable | ForEach-Object { $s = Get-Service -Name $_ -EA SilentlyContinue; if ($s -and $s.StartType -eq 'Disabled') { $_ } }) -join ', '
    "AllowTelemetry"      = (Get-ItemProperty -Path "HKLM:\Software\Policies\Microsoft\Windows\DataCollection" -Name "AllowTelemetry" -EA SilentlyContinue).AllowTelemetry
    "HighPerf Power"      = (powercfg /getactivescheme 2>$null) -replace '.*{(.*)}.*','$1'
    "Game Bar (AllowGameDVR)" = (Get-ItemProperty -Path "HKLM:\Software\Policies\Microsoft\Windows\GameDVR" -Name "AllowGameDVR" -EA SilentlyContinue).AllowGameDVR
    "Game Mode Disabled"  = (Get-ItemProperty -Path "HKLM:\Software\Policies\Microsoft\WindowsGameMode" -Name "DisableGameMode" -EA SilentlyContinue).DisableGameMode
    "Classic Context Menu" = (Test-Path "HKCU:\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32")
    "Sticky Keys Off"     = (Get-ItemProperty -Path "HKCU:\Control Panel\Accessibility\StickyKeys" -Name "Flags" -EA SilentlyContinue).Flags -eq "506"
    "Mouse Accel Off"     = (Get-ItemProperty -Path "HKCU:\Control Panel\Mouse" -Name "MouseSpeed" -EA SilentlyContinue).MouseSpeed -eq "0"
    "8.3 Names Disabled"  = (fsutil behavior query disable8dot3 2>$null) -match "1|Enabled"
    "Last Access Disabled" = (fsutil behavior query disablelastaccess 2>$null) -match "1|Enabled"
    "Hibernation Off"     = -not (Test-Path "C:\hiberfil.sys")
    "NVIDIA Telemetry"    = $nvidiaStatus
}

foreach ($k in $report.Keys) {
    $val = $report[$k]
    $status = if ($val -is [bool]) { if ($val) { "OK" } else { "NO" } } else { $val }
    $color = if ($status -eq "OK" -or $status -eq "Disabled" -or $status -eq "Created" -or $status -match "1") { "Green" } else { "Yellow" }
    Write-Host ("  {0,-28} {1}" -f $k, $status) -ForegroundColor $color
}

Write-Host "`n========================================"
Write-Host " Log: $logPath"
Write-Host "========================================`n"

Log "All sections processed. A reboot is required to apply many changes."
Write-Host 'A reboot is required to apply changes. Please reboot now.'

## Optional: ask for reboot
try {
    if (-not $WhatIf) {
        $answer = Read-Host 'Reboot now? (Y/N)'
        if ($answer -match '^[Yy]$') {
            Restart-Computer -Force
        } else {
            Write-Host 'Please reboot later to apply changes.'
            Log "User chose not to reboot immediately."
        }
    } else {
        Write-Host 'WhatIf mode: reboot not executed.'
        Log "WhatIf mode: reboot not executed."
    }
} catch { Log "ERROR on reboot prompt: $($_.Exception.Message)" }

## 0) Post-run notepad append (learnings)
try {
    $notepadDir = "D:\01_CODING\\.sisyphus\\notepads\\WIN11_LTSC_DEBLOAT"
    if (-not (Test-Path $notepadDir)) { New-Item -Path $notepadDir -ItemType Directory -Force | Out-Null }
    $notesPath = Join-Path $notepadDir 'learnings.md'
    $note = @()
    $note += "- WIN11_LTSC_DEBLOAT.ps1 run on $(Get-Date -Format 'u')"
    $note += "- Path: D:\\01_CODING\\00_N-Xyme_CATALYST\\scripts\\WIN11_LTSC_DEBLOAT.ps1"
    Add-Content -Path $notesPath -Value ($note -join [Environment]::NewLine) -Force
} catch { Log "ERROR appending to notepad: $_" }
