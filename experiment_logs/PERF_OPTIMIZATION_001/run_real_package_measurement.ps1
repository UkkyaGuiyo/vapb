$ErrorActionPreference = 'Stop'

$experimentRoot = $env:VAPB_EXPERIMENT_ROOT
$blenderPath = $env:VAPB_EXPERIMENT_ROOT
$runnerPath = Join-Path $experimentRoot 'real_package_verify.py'
$csvPath = Join-Path $experimentRoot 'after_monitor.csv'
$stdoutPath = Join-Path $experimentRoot 'blender_stdout.log'
$stderrPath = Join-Path $experimentRoot 'blender_stderr.log'
$summaryPath = Join-Path $experimentRoot 'after_process_summary.json'

$header = [pscustomobject]@{
    timestamp = $null
    blender_pid = $null
    cpu_percent = $null
    working_set_bytes = $null
    private_memory_bytes = $null
    read_bytes = $null
    write_bytes = $null
    read_ops = $null
    write_ops = $null
    thread_count = $null
    handle_count = $null
}
$header | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$started = Get-Date
$launchedProcess = Start-Process -FilePath $blenderPath -ArgumentList @('--factory-startup', '--background', '--python', $runnerPath) -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru
$targetPid = $launchedProcess.Id
$previous = $null
$sampleCount = 0

while (-not $launchedProcess.HasExited) {
    Start-Sleep -Seconds 2
    try {
        $monitorProcess = Get-Process -Id $targetPid -ErrorAction Stop
    } catch {
        break
    }
    $now = Get-Date
    $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$targetPid"
    $cpuPercent = $null
    $cpuSeconds = $monitorProcess.TotalProcessorTime.TotalSeconds
    if ($null -ne $previous) {
        $wall = ($now - $previous.timestamp).TotalSeconds
        if ($wall -gt 0) {
            $cpuPercent = [math]::Round(100.0 * ($cpuSeconds - $previous.cpu_seconds) / $wall / [Environment]::ProcessorCount, 2)
        }
    }
    $previous = [pscustomobject]@{ timestamp = $now; cpu_seconds = $cpuSeconds }
    [pscustomobject]@{
        timestamp = $now.ToString('o')
        blender_pid = $targetPid
        cpu_percent = $cpuPercent
        working_set_bytes = [int64]$monitorProcess.WorkingSet64
        private_memory_bytes = [int64]$monitorProcess.PrivateMemorySize64
        read_bytes = [int64]$cim.ReadTransferCount
        write_bytes = [int64]$cim.WriteTransferCount
        read_ops = [int64]$cim.ReadOperationCount
        write_ops = [int64]$cim.WriteOperationCount
        thread_count = [int]$monitorProcess.Threads.Count
        handle_count = [int]$monitorProcess.HandleCount
    } | Export-Csv -LiteralPath $csvPath -Append -NoTypeInformation -Encoding UTF8
    $sampleCount++
}

$ended = Get-Date
$exitCode = $null
try {
    $launchedProcess.Refresh()
    $exitCode = $launchedProcess.ExitCode
} catch { }
[ordered]@{
    blender_pid = $targetPid
    started = $started.ToString('o')
    ended = $ended.ToString('o')
    exit_code = $exitCode
    sample_count = $sampleCount
    stdout = $stdoutPath
    stderr = $stderrPath
} | ConvertTo-Json | Set-Content -LiteralPath $summaryPath -Encoding UTF8
