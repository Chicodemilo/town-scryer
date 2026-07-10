#!/bin/bash

# restore.sh - Restore database and logs
# Usage: ./scripts/restore.sh <backup_file.tar.gz>

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if backup file is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Error: No backup file specified${NC}"
    echo "Usage: ./scripts/restore.sh <backup_file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -la "$PROJECT_ROOT/backups"/*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 " bytes, " $6 " " $7 " " $8 ")"}' || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"
BACKUP_DIR="$PROJECT_ROOT/backups"

# Handle relative and absolute paths
if [[ "$BACKUP_FILE" != /* ]]; then
    # If it's just a filename, look in backups directory
    if [[ "$BACKUP_FILE" != */* ]]; then
        BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
    else
        # Relative path, make it absolute
        BACKUP_FILE="$PROJECT_ROOT/$BACKUP_FILE"
    fi
fi

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ Error: Backup file not found: $BACKUP_FILE${NC}"
    echo ""
    echo "Available backups:"
    ls -la "$BACKUP_DIR"/*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 " bytes, " $6 " " $7 " " $8 ")"}' || echo "  No backups found"
    exit 1
fi

# Extract backup name from filename
BACKUP_NAME=$(basename "$BACKUP_FILE" .tar.gz)
RESTORE_DIR="$BACKUP_DIR/restore_$BACKUP_NAME"

# Database configuration from .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please ensure .env file exists in project root"
    exit 1
fi

# Default values if not in .env (passwords must be set in .env)
MYSQL_DATABASE=${MYSQL_DATABASE:-app_db}
MYSQL_USER=${MYSQL_USER:-admin}
MYSQL_PASSWORD=${MYSQL_PASSWORD:?MYSQL_PASSWORD must be set in .env}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD must be set in .env}

echo -e "${BLUE}🔄 Starting restore process...${NC}"
echo -e "${BLUE}Backup file: $BACKUP_FILE${NC}"
echo -e "${BLUE}Backup size: $(du -h "$BACKUP_FILE" | cut -f1)${NC}"

# Function to extract backup
extract_backup() {
    echo -e "${BLUE}📦 Extracting backup archive...${NC}"
    
    # Clean up any existing restore directory
    rm -rf "$RESTORE_DIR"
    mkdir -p "$RESTORE_DIR"
    
    # Extract the backup
    cd "$BACKUP_DIR"
    tar -xzf "$BACKUP_FILE" -C "$RESTORE_DIR" --strip-components=1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Backup extracted successfully${NC}"
        echo "   Directory: $RESTORE_DIR"
        
        # Show backup info if available
        if [ -f "$RESTORE_DIR/backup_info.txt" ]; then
            echo ""
            echo -e "${BLUE}📋 Backup Information:${NC}"
            head -10 "$RESTORE_DIR/backup_info.txt" | sed 's/^/   /'
        fi
    else
        echo -e "${RED}❌ Failed to extract backup${NC}"
        return 1
    fi
}

# Function to check containers
check_containers() {
    echo -e "${BLUE}🔍 Checking container status...${NC}"
    
    if ! docker-compose -f "$PROJECT_ROOT/docker-compose.yml" ps db | grep -q "Up"; then
        echo -e "${YELLOW}⚠️  Database container is not running${NC}"
        echo "Starting database container..."
        
        docker-compose -f "$PROJECT_ROOT/docker-compose.yml" up -d db
        
        # Wait for database to be ready
        echo "Waiting for database to be ready..."
        sleep 10
        
        # Test database connection
        for i in {1..30}; do
            if docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T db mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "SELECT 1;" >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Database is ready${NC}"
                break
            fi
            echo -n "."
            sleep 2
        done
        
        if [ $i -eq 30 ]; then
            echo -e "${RED}❌ Database failed to start${NC}"
            return 1
        fi
    else
        echo -e "${GREEN}✅ Database container is running${NC}"
    fi
}

# Function to restore database
restore_database() {
    echo -e "${BLUE}📊 Restoring database...${NC}"
    
    if [ ! -f "$RESTORE_DIR/database.sql" ]; then
        echo -e "${YELLOW}⚠️  No database backup found in archive${NC}"
        return 0
    fi
    
    # Show warning about data loss
    echo -e "${YELLOW}⚠️  WARNING: This will replace all existing data in the database!${NC}"
    echo "Database: $MYSQL_DATABASE"
    echo "Backup size: $(du -h "$RESTORE_DIR/database.sql" | cut -f1)"
    echo ""
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}⏭️  Database restore skipped${NC}"
        return 0
    fi
    
    # Drop and recreate database to ensure clean state
    echo "Recreating database..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T db mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "
        DROP DATABASE IF EXISTS $MYSQL_DATABASE;
        CREATE DATABASE $MYSQL_DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        GRANT ALL PRIVILEGES ON $MYSQL_DATABASE.* TO '$MYSQL_USER'@'%';
        FLUSH PRIVILEGES;
    "
    
    # Restore database from backup
    echo "Restoring database data..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T db mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" < "$RESTORE_DIR/database.sql"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Database restored successfully${NC}"
        
        # Show some basic stats
        TABLES=$(docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T db mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "SHOW TABLES;" 2>/dev/null | wc -l)
        TABLES=$((TABLES - 1)) # Remove header line
        echo "   Tables restored: $TABLES"
    else
        echo -e "${RED}❌ Database restore failed${NC}"
        return 1
    fi
}

# Function to restore logs
restore_logs() {
    echo -e "${BLUE}📝 Restoring logs...${NC}"
    
    if [ ! -d "$RESTORE_DIR/logs" ] || [ ! "$(ls -A "$RESTORE_DIR/logs" 2>/dev/null)" ]; then
        echo -e "${YELLOW}⚠️  No logs found in backup${NC}"
        return 0
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Show warning about overwriting logs
    if [ "$(ls -A "$PROJECT_ROOT/logs" 2>/dev/null)" ]; then
        echo -e "${YELLOW}⚠️  WARNING: This will overwrite existing log files!${NC}"
        echo "Existing logs:"
        ls -la "$PROJECT_ROOT/logs/" | sed 's/^/   /'
        echo ""
        read -p "Continue with log restore? (y/N): " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}⏭️  Log restore skipped${NC}"
            return 0
        fi
    fi
    
    # Copy logs
    cp -r "$RESTORE_DIR/logs/"* "$PROJECT_ROOT/logs/"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Logs restored successfully${NC}"
        echo "   Files restored: $(ls "$PROJECT_ROOT/logs/" | wc -l | tr -d ' ')"
        echo "   Location: $PROJECT_ROOT/logs/"
    else
        echo -e "${RED}❌ Log restore failed${NC}"
        return 1
    fi
}

# Function to cleanup
cleanup() {
    echo -e "${BLUE}🧹 Cleaning up temporary files...${NC}"
    rm -rf "$RESTORE_DIR"
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Function to verify restore
verify_restore() {
    echo -e "${BLUE}🔍 Verifying restore...${NC}"
    
    # Check database connection and basic query
    if docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T db mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = '$MYSQL_DATABASE';" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Database connection verified${NC}"
    else
        echo -e "${RED}❌ Database verification failed${NC}"
        return 1
    fi
    
    # Check logs directory
    if [ -d "$PROJECT_ROOT/logs" ]; then
        echo -e "${GREEN}✅ Logs directory verified${NC}"
    else
        echo -e "${YELLOW}⚠️  Logs directory not found${NC}"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Database & Logs Restore${NC}"
    echo "=============================================="
    
    # Extract backup
    extract_backup || exit 1
    
    # Check and start containers if needed
    check_containers || exit 1
    
    # Perform restore
    restore_database || exit 1
    restore_logs
    
    # Verify restore
    verify_restore || exit 1
    
    # Cleanup
    cleanup
    
    echo ""
    echo -e "${GREEN}🎉 Restore completed successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Restart all services: ./scripts/deploy_local.sh --preserve-data"
    echo "2. Run health check: ./scripts/health_check.sh"
    echo "3. Verify your data at: http://localhost:5151"
}

# Run main function
main "$@"
