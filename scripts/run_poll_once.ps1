param(
    [switch]$SkipDoctor,
    [switch]$SkipDocker,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $ProjectRoot ".venv\bin\python.exe"
$LogDir = Join-Path $ProjectRoot ".logs"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $LogDir "poll-$Stamp.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Set-Location $ProjectRoot

function Write-Log {
    param([string]$Message)
    $line = "$(Get-Date -Format o) $Message"
    Write-Output $line
    Add-Content -Path $LogFile -Value $line
}

function Run-Step {
    param(
        [string]$Name,
        [string[]]$Arguments
    )
    Write-Log "START $Name"
    $output = & $Python @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    foreach ($line in $output) {
        Write-Log "  $line"
    }
    if ($exitCode -ne 0) {
        Write-Log "FAIL $Name exit=$exitCode"
        exit $exitCode
    }
    Write-Log "OK $Name"
}

function Run-ExternalStep {
    param(
        [string]$Name,
        [string]$Executable,
        [string[]]$Arguments
    )
    Write-Log "START $Name"
    $output = & $Executable @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    foreach ($line in $output) {
        Write-Log "  $line"
    }
    if ($exitCode -ne 0) {
        Write-Log "FAIL $Name exit=$exitCode"
        exit $exitCode
    }
    Write-Log "OK $Name"
}

Write-Log "SignalBoard poll once started"

if (-not (Test-Path $Python)) {
    Write-Log "FAIL python not found: $Python"
    exit 1
}

if (-not $SkipDocker) {
    Run-ExternalStep "docker-postgres" "docker" @("compose", "up", "-d", "postgres")
}

if (-not $SkipDoctor) {
    Run-Step "doctor-fast" @("-m", "app.cli", "doctor", "--no-check-kakao", "--no-check-naver")
}

if ($DryRun) {
    Write-Log "DryRun enabled; skipping poll"
    Write-Log "SignalBoard poll once finished"
    exit 0
}

Run-Step "poll" @("-m", "app.cli", "poll")

Write-Log "SignalBoard poll once finished"
