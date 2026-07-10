#!/bin/bash
# backup_db.sh - MySQL Database Backup Script
# Supports both manual and automated backups with rotation

set -e

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Configuration
BACKUP_DIR="./backups/db"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="backup_${TIMESTAMP}.sql"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"
RETENTION_DAYS=${DB_BACKUP_RETENTION_DAYS:-7}
COMPRESS=${DB_BACKUP_COMPRESS:-true}

# Docker compose command detection
if command -v "docker compose" &> /dev/null; then
  DC="docker compose"
elif command -v docker-compose &> /dev/null; then
  DC="docker-compose"
else
  echo "❌ Error: Neither 'docker compose' nor 'docker-compose' found"
  exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
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

# Create backup directory if it doesn't exist
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_info "Created backup directory: $BACKUP_DIR"
    fi
}

# Check if database container is running
check_db_container() {
    if ! $DC ps | grep -q 'db.*Up'; then
        log_error "Database container is not running"
        log_info "Start the database with: $DC up -d db"
        exit 1
    fi
}

# Perform database backup
backup_database() {
    log_info "Starting database backup..."
    log_info "Backup file: $BACKUP_PATH"
    
    # Create mysqldump command
    MYSQLDUMP_CMD="mysqldump -u${MYSQL_USER} -p${MYSQL_PASSWORD} --single-transaction --routines --triggers ${MYSQL_DATABASE}"
    
    # Execute backup
    if $DC exec -T db $MYSQLDUMP_CMD > "$BACKUP_PATH" 2>/dev/null; then
        log_success "Database backup completed successfully"
        
        # Get backup file size
        BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
        log_info "Backup size: $BACKUP_SIZE"
        
        # Compress backup if enabled
        if [ "$COMPRESS" = "true" ]; then
            log_info "Compressing backup..."
            gzip "$BACKUP_PATH"
            BACKUP_PATH="${BACKUP_PATH}.gz"
            COMPRESSED_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
            log_success "Backup compressed to: $COMPRESSED_SIZE"
        fi
        
        return 0
    else
        log_error "Database backup failed"
        # Clean up failed backup file
        [ -f "$BACKUP_PATH" ] && rm "$BACKUP_PATH"
        return 1
    fi
}

# Clean up old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Find and delete old backup files
    DELETED_COUNT=0
    
    # Handle both compressed and uncompressed backups
    for pattern in "backup_*.sql" "backup_*.sql.gz"; do
        find "$BACKUP_DIR" -name "$pattern" -type f -mtime +$RETENTION_DAYS -print0 | while IFS= read -r -d '' file; do
            rm "$file"
            log_info "Deleted old backup: $(basename "$file")"
            ((DELETED_COUNT++))
        done
    done
    
    if [ $DELETED_COUNT -eq 0 ]; then
        log_info "No old backups to clean up"
    else
        log_success "Cleaned up $DELETED_COUNT old backup(s)"
    fi
}

# List existing backups
list_backups() {
    log_info "Existing backups in $BACKUP_DIR:"
    echo "----------------------------------------"
    
    if [ -d "$BACKUP_DIR" ] && [ "$(ls -A $BACKUP_DIR 2>/dev/null)" ]; then
        ls -lah "$BACKUP_DIR"/backup_*.sql* 2>/dev/null | while read -r line; do
            echo "$line"
        done
    else
        log_warning "No backups found"
    fi
    echo "----------------------------------------"
}

# Restore database from backup
restore_database() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        log_error "Please specify a backup file to restore"
        list_backups
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log_warning "This will REPLACE the current database with the backup!"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled"
        exit 0
    fi
    
    log_info "Restoring database from: $backup_file"
    
    # Handle compressed files
    if [[ "$backup_file" == *.gz ]]; then
        if zcat "$backup_file" | $DC exec -T db mysql -u${MYSQL_USER} -p${MYSQL_PASSWORD} ${MYSQL_DATABASE}; then
            log_success "Database restored successfully from compressed backup"
        else
            log_error "Database restore failed"
            exit 1
        fi
    else
        if $DC exec -T db mysql -u${MYSQL_USER} -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} < "$backup_file"; then
            log_success "Database restored successfully"
        else
            log_error "Database restore failed"
            exit 1
        fi
    fi
}

# Show usage information
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  backup              Create a new database backup (default)"
    echo "  list                List existing backups"
    echo "  restore <file>      Restore database from backup file"
    echo "  cleanup             Clean up old backups"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  DB_BACKUP_RETENTION_DAYS    Days to keep backups (default: 7)"
    echo "  DB_BACKUP_COMPRESS          Compress backups (default: true)"
    echo ""
    echo "Examples:"
    echo "  $0                          # Create backup"
    echo "  $0 backup                   # Create backup"
    echo "  $0 list                     # List backups"
    echo "  $0 restore backup.sql       # Restore from backup"
    echo "  $0 cleanup                  # Clean old backups"
}

# Main script logic
main() {
    local command="${1:-backup}"
    
    case "$command" in
        backup)
            create_backup_dir
            check_db_container
            if backup_database; then
                cleanup_old_backups
                log_success "Backup process completed successfully"
            else
                log_error "Backup process failed"
                exit 1
            fi
            ;;
        list)
            list_backups
            ;;
        restore)
            check_db_container
            restore_database "$2"
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
