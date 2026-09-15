[CmdletBinding()]
param(
    [string]$ExperimentRoot = $env:VAPB_EXPERIMENT_ROOT,
    [int]$PollSeconds = 2,
    [int]$FileSnapshotSeconds = 6
)

$ErrorActionPreference = 'SilentlyContinue'
Set-StrictMode -Version 2.0

$monitorStart = Get-Date
$monitorStartUtc = $monitorStart.ToUniversalTime()
$monitorProcessId = [System.Diagnostics.Process]::GetCurrentProcess().Id
$eventsPath = Join-Path $ExperimentRoot 'events.log'
$filesystemEventsPath = Join-Path $ExperimentRoot 'filesystem_events.log'
$monitorCsvPath = Join-Path $ExperimentRoot 'monitor.csv'
$summaryPath = Join-Path $ExperimentRoot 'process_summary.json'
$stopPath = Join-Path $ExperimentRoot 'STOP_MONITOR'

New-Item -ItemType Directory -Path $ExperimentRoot -Force | Out-Null

function Get-Stamp {
    return (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
}

function Write-Event {
    param([string]$Path, [string]$Message)
    Add-Content -LiteralPath $Path -Value ((Get-Stamp) + "`t" + $Message) -Encoding UTF8
}

function Write-JsonUtf8 {
    param([string]$Path, [object]$Value)
    $json = $Value | ConvertTo-Json -Depth 8
    Set-Content -LiteralPath $Path -Value $json -Encoding UTF8
}

function Get-TargetBlenderCim {
    $items = @(Get-CimInstance Win32_Process -Filter "Name='blender.exe'")
    foreach ($item in $items) {
        $pathMatch = ($item.ExecutablePath -and ($item.ExecutablePath -like '*\Blender 4.2\blender.exe'))
        $commandMatch = ($item.CommandLine -and ($item.CommandLine -like '*Blender 4.2*'))
        if ($pathMatch -or $commandMatch) {
            $item
        }
    }
}

function Get-FileSnapshot {
    param([string]$Path)
    $fileCount = 0
    $totalSize = [int64]0
    $assetsCount = 0
    $fbxCount = 0
    $matCount = 0
    $metaCount = 0
    $textureCount = 0
    $scanErrors = 0
    try {
        foreach ($filePath in [System.IO.Directory]::EnumerateFiles($Path, '*', [System.IO.SearchOption]::AllDirectories)) {
            $fileCount++
            try {
                $fi = New-Object System.IO.FileInfo($filePath)
                $totalSize += [int64]$fi.Length
            } catch {
                $scanErrors++
            }
            $relative = $filePath.Substring($Path.Length).TrimStart('\').Replace('/', '\')
            $lowerRelative = $relative.ToLowerInvariant()
            if ($lowerRelative.StartsWith('assets\') -or $lowerRelative -eq 'assets') {
                $assetsCount++
            }
            $extension = [System.IO.Path]::GetExtension($filePath).ToLowerInvariant()
            switch ($extension) {
                '.fbx' { $fbxCount++ }
                '.mat' { $matCount++ }
                '.meta' { $metaCount++ }
                '.png' { $textureCount++ }
                '.jpg' { $textureCount++ }
                '.jpeg' { $textureCount++ }
                '.tga' { $textureCount++ }
                '.bmp' { $textureCount++ }
                '.tif' { $textureCount++ }
                '.tiff' { $textureCount++ }
                '.exr' { $textureCount++ }
                '.psd' { $textureCount++ }
            }
        }
    } catch {
        $scanErrors++
    }
    [pscustomobject]@{
        file_count = $fileCount
        total_size_bytes = $totalSize
        assets_file_count = $assetsCount
        fbx_count = $fbxCount
        mat_count = $matCount
        meta_count = $metaCount
        texture_count = $textureCount
        scan_errors = $scanErrors
    }
}

function Get-TempFolders {
    $roots = @($env:TEMP, $env:TMP) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique
    $folders = @()
    foreach ($root in $roots) {
        try {
            $folders += [System.IO.Directory]::EnumerateDirectories($root, 'unitypackage_blender_importer_*', [System.IO.SearchOption]::TopDirectoryOnly)
        } catch {
        }
    }
    return @($folders | Select-Object -Unique)
}

function Get-GpuSample {
    param([string]$Executable)
    if (-not $Executable) {
        return [pscustomobject]@{ gpu_util_percent = $null; gpu_memory_used_bytes = $null }
    }
    try {
        $line = @(& $Executable '--query-gpu=utilization.gpu,memory.used' '--format=csv,noheader,nounits' 2>$null | Select-Object -First 1)
        if ($line -and ($line -match '^\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)')) {
            return [pscustomobject]@{
                gpu_util_percent = [double]$Matches[1]
                gpu_memory_used_bytes = [int64]([double]$Matches[2] * 1024 * 1024)
            }
        }
    } catch {
    }
    return [pscustomobject]@{ gpu_util_percent = $null; gpu_memory_used_bytes = $null }
}

if (-not (Test-Path -LiteralPath $monitorCsvPath)) {
    $header = [pscustomobject]@{
        timestamp = $null
        utc_timestamp = $null
        blender_pid = $null
        blender_start_time = $null
        cpu_percent = $null
        working_set_bytes = $null
        private_memory_bytes = $null
        read_bytes = $null
        write_bytes = $null
        read_ops = $null
        write_ops = $null
        thread_count = $null
        handle_count = $null
        responding = $null
        window_title = $null
        gpu_util_percent = $null
        gpu_memory_used_bytes = $null
    }
    $header | Export-Csv -LiteralPath $monitorCsvPath -NoTypeInformation -Encoding UTF8
}

if (Test-Path -LiteralPath $stopPath) {
    throw "A stale stop sentinel already exists: $stopPath"
}

Write-Event $eventsPath ("monitor_started`tmonitor_pid=$monitorProcessId`troot=$ExperimentRoot`tpoll_seconds=$PollSeconds")
Write-Event $eventsPath 'console_capture=not_attached; external monitor does not alter Blender launch mode'

$gpuCommand = $null
$gpuCommandInfo = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($gpuCommandInfo) {
    $gpuCommand = $gpuCommandInfo.Source
    Write-Event $eventsPath ("gpu_probe_available=1`texecutable=$gpuCommand`tscope=system_gpu")
} else {
    Write-Event $eventsPath 'gpu_probe_available=0; nvidia-smi not found'
}

$initialCim = @(Get-TargetBlenderCim)
$initialPids = @($initialCim | ForEach-Object { [int]$_.ProcessId })
foreach ($cim in $initialCim) {
    Write-Event $eventsPath ("blender_seen_before_ready=1`tblender_pid=$($cim.ProcessId)`tcommand_line=$($cim.CommandLine)")
}

$previous = @{}
$folderStates = @{}
$observedPids = @{}
$exitedInitialPids = @{}
$newPids = @{}
$sampleCount = 0
$lastFileScan = @{}
$lastGpu = [pscustomobject]@{ gpu_util_percent = $null; gpu_memory_used_bytes = $null }
$lastGpuSampleIndex = -100

Write-Host 'READY_FOR_USER_ACTION'
Write-Event $eventsPath 'READY_FOR_USER_ACTION'

while (-not (Test-Path -LiteralPath $stopPath)) {
    $now = Get-Date
    $nowUtc = $now.ToUniversalTime()
    $sampleCount++

    $cims = @(Get-TargetBlenderCim)
    $currentPids = @($cims | ForEach-Object { [int]$_.ProcessId })
    foreach ($initialPid in $initialPids) {
        if (($currentPids -notcontains $initialPid) -and (-not $exitedInitialPids.ContainsKey($initialPid))) {
            $exitedInitialPids[$initialPid] = $now.ToString('o')
            Write-Event $eventsPath ("blender_initial_process_exited=1`tblender_pid=$initialPid")
        }
    }

    foreach ($cim in $cims) {
        $blenderId = [int]$cim.ProcessId
        if (-not $observedPids.ContainsKey($blenderId)) {
            $observedPids[$blenderId] = $now.ToString('o')
            if ($initialPids -notcontains $blenderId) {
                $newPids[$blenderId] = $now.ToString('o')
                Write-Event $eventsPath ("blender_new_process_seen=1`tblender_pid=$blenderId`texecutable=$($cim.ExecutablePath)")
            }
        }

        try {
            $process = Get-Process -Id $blenderId -ErrorAction Stop
            $startTime = $null
            try { $startTime = $process.StartTime.ToString('o') } catch { }
            $cpuSeconds = $process.TotalProcessorTime.TotalSeconds
            $cpuPercent = $null
            if ($previous.ContainsKey($blenderId)) {
                $prior = $previous[$blenderId]
                $wallSeconds = ($nowUtc - $prior.utc).TotalSeconds
                $cpuDelta = $cpuSeconds - $prior.cpu_seconds
                if ($wallSeconds -gt 0 -and $cpuDelta -ge 0) {
                    $cpuPercent = [math]::Round((100.0 * $cpuDelta / $wallSeconds / [Environment]::ProcessorCount), 2)
                }
            }
            $previous[$blenderId] = [pscustomobject]@{ cpu_seconds = $cpuSeconds; utc = $nowUtc }

            $readBytes = $null
            $writeBytes = $null
            $readOps = $null
            $writeOps = $null
            if ($cim.ReadTransferCount -ne $null) { $readBytes = [int64]$cim.ReadTransferCount }
            if ($cim.WriteTransferCount -ne $null) { $writeBytes = [int64]$cim.WriteTransferCount }
            if ($cim.ReadOperationCount -ne $null) { $readOps = [int64]$cim.ReadOperationCount }
            if ($cim.WriteOperationCount -ne $null) { $writeOps = [int64]$cim.WriteOperationCount }

            $responding = $null
            $windowTitle = $null
            try {
                $windowTitle = $process.MainWindowTitle
                if ($process.MainWindowHandle -ne 0) { $responding = $process.Responding }
            } catch {
            }

            if (($sampleCount - $lastGpuSampleIndex) -ge 3) {
                $lastGpu = Get-GpuSample $gpuCommand
                $lastGpuSampleIndex = $sampleCount
            }

            $row = [pscustomobject]@{
                timestamp = $now.ToString('o')
                utc_timestamp = $nowUtc.ToString('o')
                blender_pid = $blenderId
                blender_start_time = $startTime
                cpu_percent = $cpuPercent
                working_set_bytes = [int64]$process.WorkingSet64
                private_memory_bytes = [int64]$process.PrivateMemorySize64
                read_bytes = $readBytes
                write_bytes = $writeBytes
                read_ops = $readOps
                write_ops = $writeOps
                thread_count = [int]$process.Threads.Count
                handle_count = [int]$process.HandleCount
                responding = $responding
                window_title = $windowTitle
                gpu_util_percent = $lastGpu.gpu_util_percent
                gpu_memory_used_bytes = $lastGpu.gpu_memory_used_bytes
            }
            $row | Export-Csv -LiteralPath $monitorCsvPath -Append -NoTypeInformation -Encoding UTF8
        } catch {
            Write-Event $eventsPath ("process_sample_error=1`tblender_pid=$blenderId`terror=$($_.Exception.Message)")
        }
    }

    $seenFolders = @{}
    foreach ($folderPath in @(Get-TempFolders)) {
        $seenFolders[$folderPath] = $true
        if (-not $folderStates.ContainsKey($folderPath)) {
            $snapshot = Get-FileSnapshot $folderPath
            $folderStates[$folderPath] = [ordered]@{
                path = $folderPath
                created_observed = $now.ToString('o')
                last_seen = $now.ToString('o')
                last_scan = $now.ToString('o')
                miss_count = 0
                snapshot = $snapshot
            }
            $lastFileScan[$folderPath] = $now
            Write-Event $filesystemEventsPath ("event=created`tfolder=$folderPath`tfile_count=$($snapshot.file_count)`ttotal_size_bytes=$($snapshot.total_size_bytes)`tassets_file_count=$($snapshot.assets_file_count)`tfbx_count=$($snapshot.fbx_count)`tmat_count=$($snapshot.mat_count)`tmeta_count=$($snapshot.meta_count)`ttexture_count=$($snapshot.texture_count)")
            Write-Event $eventsPath ("temp_folder_created=1`tfolder=$folderPath")
        } else {
            $state = $folderStates[$folderPath]
            $state.last_seen = $now.ToString('o')
            $state.miss_count = 0
            if (-not $lastFileScan.ContainsKey($folderPath) -or (($now - $lastFileScan[$folderPath]).TotalSeconds -ge $FileSnapshotSeconds)) {
                $state.snapshot = Get-FileSnapshot $folderPath
                $state.last_scan = $now.ToString('o')
                $lastFileScan[$folderPath] = $now
            }
        }
    }

    foreach ($folderPath in @($folderStates.Keys)) {
        if (-not $seenFolders.ContainsKey($folderPath)) {
            $state = $folderStates[$folderPath]
            $state.miss_count = [int]$state.miss_count + 1
            if ($state.miss_count -ge 2 -and -not $state.Contains('deleted_observed')) {
                $state.deleted_observed = $now.ToString('o')
                $snapshot = $state.snapshot
                Write-Event $filesystemEventsPath ("event=deleted`tfolder=$folderPath`tcreated=$($state.created_observed)`tdeleted=$($state.deleted_observed)`tfile_count=$($snapshot.file_count)`ttotal_size_bytes=$($snapshot.total_size_bytes)`tassets_file_count=$($snapshot.assets_file_count)`tfbx_count=$($snapshot.fbx_count)`tmat_count=$($snapshot.mat_count)`tmeta_count=$($snapshot.meta_count)`ttexture_count=$($snapshot.texture_count)")
                Write-Event $eventsPath ("temp_folder_deleted=1`tfolder=$folderPath")
            }
        }
    }

    Start-Sleep -Seconds $PollSeconds
}

$monitorEnd = Get-Date
foreach ($folderPath in @($folderStates.Keys)) {
    $state = $folderStates[$folderPath]
    if (-not $state.Contains('deleted_observed')) {
        $snapshot = $state.snapshot
        Write-Event $filesystemEventsPath ("event=still_present_at_stop`tfolder=$folderPath`LastSeen=$($state.last_seen)`tfile_count=$($snapshot.file_count)`ttotal_size_bytes=$($snapshot.total_size_bytes)`tassets_file_count=$($snapshot.assets_file_count)`tfbx_count=$($snapshot.fbx_count)`tmat_count=$($snapshot.mat_count)`tmeta_count=$($snapshot.meta_count)`ttexture_count=$($snapshot.texture_count)")
    }
}

$summary = [ordered]@{
    experiment = 'CASE_A_REAL_PACKAGE_IMPORT_MONITOR_001'
    monitor_start = $monitorStart.ToString('o')
    monitor_end = $monitorEnd.ToString('o')
    monitor_pid = $monitorProcessId
    poll_seconds = $PollSeconds
    file_snapshot_seconds = $FileSnapshotSeconds
    sample_count = $sampleCount
    initial_blender_pids = @($initialPids)
    initial_blender_exited = @($exitedInitialPids.Keys)
    observed_blender_pids = @($observedPids.Keys)
    new_blender_pids_after_ready = @($newPids.Keys)
    restart_observed = (($initialPids.Count -gt 0) -and ($exitedInitialPids.Count -gt 0) -and ($newPids.Count -gt 0))
    gpu_probe = [bool]$gpuCommand
    gpu_probe_executable = $gpuCommand
    console_capture = $false
    temp_folder_count = $folderStates.Count
    temp_folders = @($folderStates.Values | ForEach-Object {
        [ordered]@{
            path = $_.path
            created_observed = $_.created_observed
            deleted_observed = $_.deleted_observed
            last_seen = $_.last_seen
            snapshot = $_.snapshot
        }
    })
}
Write-JsonUtf8 $summaryPath $summary
Write-Event $eventsPath ("monitor_stopped`tmonitor_end=$($monitorEnd.ToString('o'))`tsamples=$sampleCount")
Write-Host 'MONITOR_STOPPED'
