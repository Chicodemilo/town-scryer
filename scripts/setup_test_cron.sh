#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_TESTS="$SCRIPT_DIR/run_tests.sh"

# Make sure run_tests.sh is executable
chmod +x "$RUN_TESTS"

# Add nightly cron job (2 AM)
CRON_ENTRY="0 2 * * * $RUN_TESTS >> /tmp/test_cron.log 2>&1"

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -qF "$RUN_TESTS"; then
  echo "Cron job already exists."
else
  (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
  echo "Nightly test cron job added (runs at 2 AM)."
fi

echo "Current crontab:"
crontab -l
