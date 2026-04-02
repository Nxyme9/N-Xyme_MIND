<# Performance audit script (PowerShell)
Gathers: CPU, memory, disk I/O, GPU, and network metrics.
Outputs: JSON with a snapshot of current system performance.
#>
$cpuSample = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 60).CounterSamples
$cpuAvg = ($cpuSample | ForEach-Object { $_.CookedValue } | Measure-Object -Average | Select-Object -ExpandProperty Average)
$cpuMax = ($cpuSample | ForEach-Object { $_.CookedValue } | Measure-Object -Maximum | Select-Object -ExpandProperty Maximum)

$os = Get-CimInstance Win32_OperatingSystem
$memoryTotalMB = [math]::Round($os.TotalVisibleMemorySize/1024,0)
$memoryFreeMB = [math]::Round($os.FreePhysicalMemory/1024,0)
$memoryUsedMB = $memoryTotalMB - $memoryFreeMB

$diskBytesSec = (Get-Counter '\PhysicalDisk(_Total)\Disk Bytes/sec').CounterSamples | ForEach-Object { $_.CookedValue } | Measure-Object -Average | Select-Object -ExpandProperty Average
$diskReadBytesSec = (Get-Counter '\PhysicalDisk(_Total)\Disk Read Bytes/sec').CounterSamples | ForEach-Object { $_.CookedValue } | Measure-Object -Average | Select-Object -ExpandProperty Average
$diskWriteBytesSec = (Get-Counter '\PhysicalDisk(_Total)\Disk Write Bytes/sec').CounterSamples | ForEach-Object { $_.CookedValue } | Measure-Object -Average | Select-Object -ExpandProperty Average

$gpuInfo = $null
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
  try {
    $gpuInfo = & nvidia-smi --query-gpu=name,utilization.gpu,memory.total,memory.used --format=csv,noheader,nounits
  } catch {
    $gpuInfo = "N/A"
  }
} else {
  $gpuInfo = "NVIDIA not found"
}

$ping = Test-Connection -ComputerName 8.8.8.8 -Count 5 -ErrorAction SilentlyContinue
$networkLatencyMs = if ($ping) { [math]::Round(($ping | Measure-Object -Property ResponseTime -Average | Select-Object -ExpandProperty Average),0) } else { -1 }

$report = @{
  timestamp = (Get-Date).ToString("o")
  cpuAvgPercent = [math]::Round($cpuAvg,2)
  cpuMaxPercent = [math]::Round($cpuMax,2)
  memoryTotalMB = $memoryTotalMB
  memoryUsedMB = [math]::Round($memoryUsedMB,0)
  memoryFreeMB = $memoryFreeMB
  diskBytesPerSec = [math]::Round($diskBytesSec,0)
  diskReadBytesPerSec = [math]::Round($diskReadBytesSec,0)
  diskWriteBytesPerSec = [math]::Round($diskWriteBytesSec,0)
  gpuInfo = $gpuInfo
  networkLatencyMs = $networkLatencyMs
}
$report | ConvertTo-Json -Depth 4
