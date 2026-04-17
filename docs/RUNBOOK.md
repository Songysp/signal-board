# SignalBoard Local Runbook

## Safe Polling Policy

SignalBoard defaults to a 4-hour polling interval to reduce Naver rate-limit and blocking risk.

Do not use unattended polling below 4 hours.

Do not bypass Captcha, rotate IPs, use private login sessions, or work around rate limits.

## One-Time Readiness Check

```powershell
docker compose up -d postgres
.\.venv\bin\python.exe -m app.cli init-db
.\.venv\bin\python.exe -m app.cli doctor
```

## Run One Poll Manually

This command checks local readiness without sending a Kakao test message, then runs one DB-backed poll.
It also starts the local PostgreSQL container with `docker compose up -d postgres` unless `-SkipDocker` is provided.

```powershell
.\scripts\run_poll_once.ps1
```

Dry run without polling:

```powershell
.\scripts\run_poll_once.ps1 -DryRun
```

Skip Docker startup if PostgreSQL is managed separately:

```powershell
.\scripts\run_poll_once.ps1 -SkipDocker
```

Logs are written to:

```text
.logs\poll-YYYYMMDD-HHMMSS.log
```

## Install Windows Scheduled Task

This creates a local Windows Scheduled Task named `SignalBoardPoll`.

The default interval is 4 hours.

```powershell
.\scripts\install_windows_task.ps1
```

Custom task name:

```powershell
.\scripts\install_windows_task.ps1 -TaskName "SignalBoardPollLocal" -IntervalHours 4
```

The install script refuses intervals below 4 hours.

## Check Scheduled Task

```powershell
Get-ScheduledTask -TaskName SignalBoardPoll
Get-ScheduledTaskInfo -TaskName SignalBoardPoll
```

## Remove Scheduled Task

```powershell
.\scripts\uninstall_windows_task.ps1
```

## Operational Notes

- Keep Docker Desktop running so PostgreSQL is available.
- Keep `.env` and `.signalboard.tokens.json` in the project folder.
- Use the management UI to disable old test watches before enabling unattended polling.
- Use `doctor` when anything looks wrong.
