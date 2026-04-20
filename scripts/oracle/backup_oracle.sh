#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/signal-board}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/signalboard-backups}"

cd "$APP_DIR"
set -a
source .env
set +a

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/signalboard-$(date +%Y%m%d-%H%M%S).sql"

docker compose -f compose.prod.yaml exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-signalboard}" \
  "${POSTGRES_DB:-signalboard}" \
  > "$BACKUP_FILE"

echo "[SignalBoard] Backup written: $BACKUP_FILE"
