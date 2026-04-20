#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/signal-board}"

cd "$APP_DIR"

if [ ! -f ".env" ]; then
  echo "Missing .env. Run bootstrap_oracle.sh first or copy .env.prod.example to .env."
  exit 1
fi

echo "[SignalBoard] Pulling latest main"
git pull --ff-only

echo "[SignalBoard] Building and starting containers"
docker compose -f compose.prod.yaml up -d --build

echo "[SignalBoard] Initializing database"
docker compose -f compose.prod.yaml exec app python -m app.cli init-db

echo "[SignalBoard] Running doctor"
docker compose -f compose.prod.yaml exec app python -m app.cli doctor --no-check-kakao

echo "[SignalBoard] Deployment complete"
docker compose -f compose.prod.yaml ps
