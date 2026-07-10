#!/bin/bash
# deploy_gcp.sh - Scaffold for GCP deployment (work in progress)

set -e
set -o pipefail
set -x  # Print each command as it runs for debugging

trap 'echo "[deploy_gcp.sh] ERROR: Script failed at line $LINENO. Last command: $BASH_COMMAND" >&2' ERR

# Detect docker compose command (prefer new, fallback to old)
if command -v "docker compose" &> /dev/null; then
  DC="docker compose"
elif command -v docker-compose &> /dev/null; then
  DC="docker-compose"
else
  echo "Neither 'docker compose' nor 'docker-compose' found. Please install Docker Compose." >&2
  exit 1
fi

# TODO: Add teardown logic for GCP containers and cache here
# Example (for local):
# $DC down --remove-orphans
# docker builder prune -f
# docker system prune -af

# TODO: Add authentication and project config
# Example: gcloud auth login
# Example: gcloud config set project <PROJECT_ID>

# TODO: Build and push Docker images to Google Container Registry
# Example:
# docker build -t gcr.io/$GCP_PROJECT_ID/shirtforge-backend ./backend
# docker push gcr.io/$GCP_PROJECT_ID/shirtforge-backend

# TODO: Deploy to Cloud Run, set up Cloud SQL, etc.
# Example:
# gcloud run deploy backend --image gcr.io/$GCP_PROJECT_ID/shirtforge-backend --platform managed --region us-central1

# Placeholder for now

echo "GCP deployment script is a work in progress. Please see comments for next steps."

# Run health check after deployment (will work once GCP endpoints are set up)
echo
echo "============================="
echo " Running GCP Health Check"
echo "============================="
./health_check.sh
