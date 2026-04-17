# SignalBoard Production Readiness Checklist

SignalBoard is currently a local MVP for conservative, low-frequency monitoring.

Use this checklist before enabling unattended polling.

## Required

- [ ] Docker Desktop is running.
- [ ] PostgreSQL container is healthy.
- [ ] `.env` exists and contains `DATABASE_URL`.
- [ ] Kakao self-message works.
- [ ] `KAKAO_REFRESH_TOKEN` is present, or the operator understands that Kakao access token expiry can stop alerts.
- [ ] `NAVER_SEARCH_URL` or at least one active watch is configured.
- [ ] Only intended watch targets are active.
- [ ] `doctor` passes without `FAIL`.
- [ ] `run_poll_once.ps1 -DryRun` succeeds.
- [ ] Poll interval is 4 hours or greater.

## Recommended

- [ ] `SIGNALBOARD_ADMIN_TOKEN` is set if the management UI is reachable outside the local machine.
- [ ] Old test watches are disabled from the management UI.
- [ ] Recent alerts are reviewed in the dashboard.
- [ ] Current results are reviewed for each active watch.
- [ ] Retention cleanup dry-run has been checked.
- [ ] Windows Scheduled Task is installed only after the dry-run passes.

## Commands

```powershell
docker compose up -d postgres
.\.venv\bin\python.exe -m app.cli init-db
.\.venv\bin\python.exe -m app.cli doctor
.\scripts\run_poll_once.ps1 -DryRun
```

Install scheduler:

```powershell
.\scripts\install_windows_task.ps1
```

Remove scheduler:

```powershell
.\scripts\uninstall_windows_task.ps1
```

## Current MVP Limits

- Search result monitoring is complex/cluster-level, not individual article-level.
- Individual listing extraction is blocked until a safe complex-to-article path is available.
- Kakao friend/channel sending is not part of the current MVP.
- Do not bypass Naver rate limits, Captcha, login restrictions, or IP controls.
