#!/usr/bin/env bash
set -euo pipefail

# start.sh — Launch the project with a custom name
# Usage: ./start.sh "My Cool App"
# Falls back to APP_NAME from .env, then "Town Scryer"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Auto-create .env from .env.example if it doesn't exist
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "Created .env from .env.example (edit passwords before production use)"
fi

# Load .env if it exists
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# Use CLI arg if provided, otherwise fall back to env/default
if [ -n "${1:-}" ]; then
  export APP_NAME="$1"
  shift
fi
APP_NAME="${APP_NAME:-Town Scryer}"

# Slugify for Docker: lowercase, spaces to hyphens, strip non-alphanumeric
SLUG=$(echo "$APP_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-')
export COMPOSE_PROJECT_NAME="$SLUG"

# Pass to frontend (Vite)
export VITE_APP_NAME="$APP_NAME"

echo "========================================="
echo "  Starting: $APP_NAME"
echo "  Compose project: $SLUG"
echo "========================================="

docker compose up --build "$@"
