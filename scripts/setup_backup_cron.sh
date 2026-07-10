#!/bin/bash
# setup_backup_cron.sh - Setup automated database backups via cron

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup_db.sh"

# Default backup schedule (daily at 2 AM)
DEFAULT_SCHEDULE="0 2 * * *"

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -s, --schedule CRON    Cron schedule (default: '$DEFAULT_SCHEDULE')"
    echo "  -r, --remove           Remove existing backup cron job"
    echo "  -l, --list             List current backup cron jobs"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Setup daily backup at 2 AM"
    echo "  $0 -s '0 */6 * * *'                 # Setup backup every 6 hours"
    echo "  $0 -s '0 2 * * 0'                   # Setup weekly backup on Sunday at 2 AM"
    echo "  $0 --remove                          # Remove backup cron job"
    echo "  $0 --list                            # List current cron jobs"
}

setup_cron_job() {
    local schedule="$1"
    local cron_command="cd $PROJECT_DIR && $BACKUP_SCRIPT backup >> $PROJECT_DIR/logs/backup.log 2>&1"
    local cron_entry="$schedule $cron_command"
    
    log_info "Setting up automated database backup..."
    log_info "Schedule: $schedule"
    log_info "Command: $cron_command"
    
    # Create logs directory if it doesn't exist
    mkdir -p "$PROJECT_DIR/logs"
    
    # Remove existing backup cron job if it exists
    remove_cron_job_silent
    
    # Add new cron job
    (crontab -l 2>/dev/null; echo "$cron_entry") | crontab -
    
    log_success "Automated backup cron job added successfully"
    log_info "Backup logs will be written to: $PROJECT_DIR/logs/backup.log"
    log_info "You can monitor backups with: tail -f $PROJECT_DIR/logs/backup.log"
}

remove_cron_job() {
    log_info "Removing automated database backup cron job..."
    
    if remove_cron_job_silent; then
        log_success "Backup cron job removed successfully"
    else
        log_warning "No backup cron job found to remove"
    fi
}

remove_cron_job_silent() {
    # Remove cron job containing the backup script path
    local temp_cron=$(mktemp)
    crontab -l 2>/dev/null | grep -v "$BACKUP_SCRIPT" > "$temp_cron" || true
    
    # Check if anything was removed
    local original_lines=$(crontab -l 2>/dev/null | wc -l)
    local new_lines=$(cat "$temp_cron" | wc -l)
    
    crontab "$temp_cron"
    rm "$temp_cron"
    
    # Return success if lines were removed
    [ "$original_lines" -gt "$new_lines" ]
}

list_cron_jobs() {
    log_info "Current cron jobs related to database backup:"
    echo "----------------------------------------"
    
    local backup_jobs=$(crontab -l 2>/dev/null | grep "$BACKUP_SCRIPT" || true)
    
    if [ -n "$backup_jobs" ]; then
        echo "$backup_jobs"
    else
        log_warning "No automated backup cron jobs found"
    fi
    
    echo "----------------------------------------"
    log_info "All current cron jobs:"
    echo "----------------------------------------"
    crontab -l 2>/dev/null || log_warning "No cron jobs found"
    echo "----------------------------------------"
}

validate_cron_schedule() {
    local schedule="$1"
    
    # Basic validation - should have 5 fields
    local field_count=$(echo "$schedule" | wc -w)
    if [ "$field_count" -ne 5 ]; then
        log_error "Invalid cron schedule format. Expected 5 fields (minute hour day month weekday)"
        log_info "Example: '0 2 * * *' for daily at 2 AM"
        return 1
    fi
    
    return 0
}

main() {
    local schedule="$DEFAULT_SCHEDULE"
    local action="setup"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--schedule)
                schedule="$2"
                shift 2
                ;;
            -r|--remove)
                action="remove"
                shift
                ;;
            -l|--list)
                action="list"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Check if backup script exists
    if [ ! -f "$BACKUP_SCRIPT" ]; then
        log_error "Backup script not found: $BACKUP_SCRIPT"
        exit 1
    fi
    
    case "$action" in
        setup)
            if validate_cron_schedule "$schedule"; then
                setup_cron_job "$schedule"
            else
                exit 1
            fi
            ;;
        remove)
            remove_cron_job
            ;;
        list)
            list_cron_jobs
            ;;
    esac
}

main "$@"
