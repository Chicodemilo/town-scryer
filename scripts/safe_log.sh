#!/bin/bash
# safe_log.sh - Append a message to a log file in the top-level /logs directory.
# safe_log.sh - Append a message to change_log.txt or known_issues.txt with a timestamp

set -e

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <change_log|known_issues> \"Your message here\""
  exit 1
fi

LOG_TYPE="$1"
shift
MESSAGE="$*"

# This assumes the script is run from the project root.
case "$LOG_TYPE" in
  change_log)
    LOG_FILE="logs/change_log.txt"
    ;;
  known_issues)
    LOG_FILE="logs/known_issues.txt"
    ;;
  *)
    echo "Invalid log type: $LOG_TYPE. Use 'change_log' or 'known_issues'."
    exit 1
    ;;
esac

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo -e "[$TIMESTAMP] $MESSAGE\n\n" >> "$LOG_FILE"
echo "Logged to $LOG_FILE: [$TIMESTAMP] $MESSAGE"
