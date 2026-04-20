#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Songysp/signal-board.git}"
APP_DIR="${APP_DIR:-$HOME/signal-board}"

echo "[SignalBoard] Installing base packages"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl git
else
  echo "Unsupported OS: apt-get not found. Install Docker and git manually, then run deploy_oracle.sh."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[SignalBoard] Installing Docker"
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
else
  echo "[SignalBoard] Docker already installed"
fi

if [ ! -d "$APP_DIR/.git" ]; then
  echo "[SignalBoard] Cloning repository to $APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
else
  echo "[SignalBoard] Repository already exists at $APP_DIR"
fi

cd "$APP_DIR"

if [ ! -f ".env" ]; then
  echo "[SignalBoard] Creating .env from .env.prod.example"
  cp .env.prod.example .env
  echo "[SignalBoard] Edit .env before starting services:"
  echo "  nano $APP_DIR/.env"
else
  echo "[SignalBoard] .env already exists"
fi

echo "[SignalBoard] Bootstrap complete"
echo "Next:"
echo "  cd $APP_DIR"
echo "  nano .env"
echo "  ./scripts/oracle/deploy_oracle.sh"
