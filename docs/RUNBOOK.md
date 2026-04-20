# SignalBoard Local Runbook

## Safe Polling Policy

SignalBoard defaults to a 4-hour polling interval to reduce Naver rate-limit and blocking risk.

Do not use unattended polling below 4 hours.

Do not bypass Captcha, rotate IPs, use private login sessions, or work around rate limits.

Before enabling unattended polling, review:

```text
docs\PRODUCTION_READINESS.md
```

## One-Time Readiness Check

```powershell
docker compose up -d postgres
.\.venv\bin\python.exe -m app.cli init-db
.\.venv\bin\python.exe -m app.cli doctor
```

## Kakao Token Longevity

Long-running polling works best with a refresh token.

If `doctor` reports `KAKAO_REFRESH_TOKEN` as missing, run:

```powershell
.\.venv\bin\python.exe -m app.cli kakao-login
```

Refresh manually when needed:

```powershell
.\.venv\bin\python.exe -m app.cli kakao-refresh
```

## Slack Notification

If `SLACK_WEBHOOK_URL` is set in `.env`, SignalBoard sends alert messages to Slack in addition to Kakao.

Test Slack delivery:

```powershell
.\.venv\bin\python.exe -m app.cli send-test-slack
```

Keep the webhook URL secret and never commit it.

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

## Retention Cleanup

Dry-run old alert events and local log files:

```powershell
.\.venv\bin\python.exe -m app.cli cleanup-retention --days 30
```

Apply cleanup:

```powershell
.\.venv\bin\python.exe -m app.cli cleanup-retention --days 30 --apply
```

## Operational Notes

- Keep Docker Desktop running so PostgreSQL is available.
- Keep `.env` and `.signalboard.tokens.json` in the project folder.
- Use the management UI to disable old test watches before enabling unattended polling.
- Use `doctor` when anything looks wrong.
- For shared networks, set `SIGNALBOARD_ADMIN_TOKEN` in `.env` and enter the same value in the management UI.
