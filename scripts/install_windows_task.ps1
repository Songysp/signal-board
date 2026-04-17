param(
    [string]$TaskName = "SignalBoardPoll",
    [int]$IntervalHours = 4
)

$ErrorActionPreference = "Stop"

if ($IntervalHours -lt 4) {
    throw "IntervalHours must be 4 or greater to respect the Naver safe polling policy."
}

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ScriptPath = Join-Path $ProjectRoot "scripts\run_poll_once.ps1"

if (-not (Test-Path $ScriptPath)) {
    throw "Missing poll script: $ScriptPath"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""

$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(5) `
    -RepetitionInterval (New-TimeSpan -Hours $IntervalHours) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "SignalBoard safe polling every $IntervalHours hours" `
    -Force | Out-Null

Write-Output "Installed Windows Scheduled Task: $TaskName"
Write-Output "Interval: every $IntervalHours hours"
Write-Output "Script: $ScriptPath"
