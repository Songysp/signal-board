#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/signal-board}"
SERVICE="${1:-app}"

cd "$APP_DIR"
docker compose -f compose.prod.yaml logs -f "$SERVICE"
