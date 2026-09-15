$ErrorActionPreference = 'Stop'
$root = $env:VAPB_EXPERIMENT_ROOT
$events = Join-Path $root 'debug_events.log'
New-Item -ItemType Directory -Path $root -Force | Out-Null
Set-Content -LiteralPath $events -Value 'before' -Encoding UTF8
Add-Content -LiteralPath $events -Value ((Get-Date).ToString('o') + "`t" + 'after') -Encoding UTF8
Write-Host 'DEBUG_WRITE_OK'
