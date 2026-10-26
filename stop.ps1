<#
.SYNOPSIS
  Stops what .\demo.ps1 started: the portal, the agent and (when it started one) the local panel.
#>
$Kit = Split-Path -Parent $MyInvocation.MyCommand.Path
$State = Join-Path $Kit ".demo"
$PidFile = Join-Path $State "pids"
if (Test-Path $PidFile) {
    foreach ($id in Get-Content $PidFile) {
        if (-not $id) { continue }
        & taskkill /PID $id /T /F 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-Host "  stopped pid $id" }
    }
    Remove-Item -Force $PidFile
}
$started = Join-Path $State "panel\started"
$dirFile = Join-Path $State "sentrai-dir"
if ((Test-Path $started) -and (Test-Path $dirFile)) {
    $stop = Join-Path (Get-Content $dirFile | Select-Object -First 1).Trim() "mvp\stop.ps1"
    if (Test-Path $stop) { & powershell -NoProfile -ExecutionPolicy Bypass -File $stop }
    Remove-Item -Force $started
}
Write-Host "Demo lab stopped. Its data stays in .demo\ (delete that folder for a fresh start)."
