# Oracle Cloud Docker Deployment

This runbook deploys SignalBoard on an Oracle Cloud VM with Docker Compose.

The recommended admin access model is SSH tunneling. Do not expose the admin UI directly to the public internet for the MVP.

## Target Architecture

```text
Oracle VM
├─ postgres container
├─ app container      FastAPI/admin UI on 127.0.0.1:8000
└─ worker container   python -m app.cli poll-loop, default 4 hours
```

Notifications:

- Slack Webhook is recommended for server operation.
- Kakao is optional and can remain paused.

## 1. Install Docker

On Oracle Linux or Ubuntu, install Docker using your preferred OS method.

Ubuntu example:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
docker --version
docker compose version
```

## 2. Clone Repository

```bash
cd ~
git clone https://github.com/Songysp/signal-board.git
cd signal-board
```

## 3. Create Environment File

```bash
cp .env.prod.example .env
nano .env
```

Required values:

- `POSTGRES_PASSWORD`
- `SLACK_WEBHOOK_URL`
- `NAVER_SEARCH_URL` or watches registered later through the admin UI
- `SIGNALBOARD_ADMIN_TOKEN` if you will use the admin UI through a tunnel

Kakao can stay empty if Slack is enough.

## 4. Start Services

```bash
docker compose -f compose.prod.yaml up -d --build
```

Initialize DB:

```bash
docker compose -f compose.prod.yaml exec app python -m app.cli init-db
```

Run doctor:

```bash
docker compose -f compose.prod.yaml exec app python -m app.cli doctor --no-check-kakao
```

## 5. Access Admin UI With SSH Tunnel

On your Windows PC:

```powershell
ssh -L 8000:127.0.0.1:8000 opc@ORACLE_PUBLIC_IP
```

Open:

```text
http://127.0.0.1:8000/
```

If `SIGNALBOARD_ADMIN_TOKEN` is set, enter it in the admin UI token field before running mutating actions.

## 6. Logs

```bash
docker compose -f compose.prod.yaml logs -f app
docker compose -f compose.prod.yaml logs -f worker
docker compose -f compose.prod.yaml logs -f postgres
```

## 7. Redeploy

```bash
cd ~/signal-board
git pull
docker compose -f compose.prod.yaml up -d --build
docker compose -f compose.prod.yaml exec app python -m app.cli init-db
```

## 8. Stop

```bash
docker compose -f compose.prod.yaml down
```

Do not delete the volume unless you intentionally want to remove PostgreSQL data.

## 9. Backup PostgreSQL

```bash
mkdir -p ~/signalboard-backups
docker compose -f compose.prod.yaml exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-signalboard}" \
  "${POSTGRES_DB:-signalboard}" \
  > ~/signalboard-backups/signalboard-$(date +%Y%m%d-%H%M%S).sql
```

## 10. Safety Notes

- `app` is bound to `127.0.0.1:8000`, so use SSH tunneling.
- `worker` uses `poll-loop`, whose default interval is 4 hours.
- Do not lower unattended polling below 4 hours.
- Do not bypass Naver rate limits or access controls.
- Keep `.env` private.
