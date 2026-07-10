#!/bin/bash
# deploy_local.sh - Deploy the application locally using Docker Compose
# Usage: ./deploy_local.sh [--preserve-data|-p]

set -e
set -o pipefail
# set -x  # Print each command as it runs for debugging (disabled for cleaner output)

trap 'echo "[deploy_local.sh] ERROR: Script failed at line $LINENO. Last command: $BASH_COMMAND" >&2' ERR

# Parse command line arguments
PRESERVE_DATA=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --preserve-data|-p)
      PRESERVE_DATA=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--preserve-data|-p]"
      echo "  --preserve-data, -p    Preserve existing database data (skip init scripts)"
      echo "  --help, -h            Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Detect docker compose command (prefer new, fallback to old)
if command -v "docker compose" &> /dev/null; then
  DC="docker compose"
elif command -v docker-compose &> /dev/null; then
  DC="docker-compose"
else
  echo "Neither 'docker compose' nor 'docker-compose' found. Please install Docker Compose." >&2
  exit 1
fi

echo "[deploy_local.sh] Taking down any existing containers and networks..."
$DC down --remove-orphans
# Optional: clear Docker build cache (uncomment if needed)
# docker builder prune -f
# docker system prune -af

# Copy .env.example to .env if .env doesn't exist
if [ ! -f .env ]; then
  echo "Copying .env.example to .env..."
  cp .env.example .env
fi

# Load environment variables from .env file
if [ -f .env ]; then
  echo "Loading environment variables from .env..."
  export $(grep -v '^#' .env | xargs)
fi

# Build and start all services

if [ "$PRESERVE_DATA" = true ]; then
  echo "🔄 Preserving data: Stopping containers without removing volumes..."
  $DC down
else
  echo "🆕 Fresh deployment: Tearing down existing containers and volumes..."
  $DC down -v
fi

echo "Clearing Docker build cache and removing project images..."
docker builder prune -f
docker images | grep myapp | awk '{print $3}' | xargs -r docker rmi -f || echo "Note: Some images couldn't be removed (may be in use)"

if [ "$PRESERVE_DATA" = true ]; then
  echo "🔄 Building and starting services with data preservation..."
  $DC -f docker-compose.yml -f docker-compose.preserve.yml up --build -d
else
  echo "🆕 Building and starting services with fresh data..."
  $DC -f docker-compose.yml -f docker-compose.fresh.yml up --build -d
fi

# Wait for MySQL container to be ready and create tables
echo
echo "============================="
echo " Waiting for MySQL to be ready"
echo "============================="

# Wait for MySQL container to be ready (max 30 tries, 15 seconds each = 7.5 minutes)
MAX_TRIES=30
TRY_COUNT=0
MYSQL_READY=false

while [ $TRY_COUNT -lt $MAX_TRIES ]; do
  TRY_COUNT=$((TRY_COUNT + 1))
  echo "[Attempt $TRY_COUNT/$MAX_TRIES] Checking MySQL readiness..."
  
  # Test MySQL connection
  if $DC exec -T db mysqladmin ping -h localhost -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" --silent 2>/dev/null; then
    echo "✅ MySQL is ready!"
    MYSQL_READY=true
    break
  else
    echo "⏳ MySQL not ready yet, waiting 15 seconds..."
    sleep 15
  fi
done

if [ "$MYSQL_READY" = true ]; then
  if [ "$PRESERVE_DATA" = true ]; then
    echo "✅ MySQL is ready with preserved data!"
  else
    echo "✅ MySQL is ready and tables are initialized via init script!"
  fi
else
  echo "❌ MySQL failed to become ready after $MAX_TRIES attempts"
  echo "MySQL container logs:"
  $DC logs db | tail -20
  exit 1
fi

# Show recent logs for each main container
for svc in api frontend db; do
  echo
  echo "============================="
  echo " Recent logs for $svc container"
  echo "============================="
  $DC logs --tail=20 $svc || echo "[warn] Could not fetch logs for $svc"
done

# Run health check after deployment
echo
echo "============================="
echo " Running Local Health Check"
echo "============================="
./scripts/health_check.sh -e local
