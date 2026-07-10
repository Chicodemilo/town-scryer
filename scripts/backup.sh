#!/bin/bash

# backup.sh - Backup database and logs
# Usage: ./scripts/backup.sh [backup_name]
# If no backup_name provided, uses timestamp

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

# Default backup name with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="${1:-backup_$TIMESTAMP}"

# Backup directory
BACKUP_DIR="$PROJECT_ROOT/backups"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

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

echo -e "${BLUE}🔄 Starting backup process...${NC}"
echo -e "${BLUE}Backup name: ${BACKUP_NAME}${NC}"

# Create backup directory
mkdir -p "$BACKUP_PATH"

# Function to check if containers are running
check_containers() {
    if ! docker-compose -f "$PROJECT_ROOT/docker-compose.yml" ps | grep -q "Up"; then
        echo -e "${YELLOW}⚠️  Warning: No containers appear to be running${NC}"
        echo "You may want to start the services first with:"
        echo "  ./scripts/deploy_local.sh"
        echo ""
        read -p "Continue with backup anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}❌ Backup cancelled${NC}"
            exit 1
        fi
    fi
}

# Function to backup database
backup_database() {
    echo -e "${BLUE}📊 Backing up database...${NC}"
    
    # Check if db container is running
    if ! docker-compose -f "$PROJECT_ROOT/docker-compose.yml" ps db | grep -q "Up"; then
        echo -e "${RED}❌ Database container is not running${NC}"
        return 1
    fi
    
    # Create database dump
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T db mysqldump \
        -u root -p"$MYSQL_ROOT_PASSWORD" \
        --single-transaction \
        --routines \
        --triggers \
        "$MYSQL_DATABASE" > "$BACKUP_PATH/database.sql"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Database backup completed${NC}"
        echo "   File: $BACKUP_PATH/database.sql"
        echo "   Size: $(du -h "$BACKUP_PATH/database.sql" | cut -f1)"
    else
        echo -e "${RED}❌ Database backup failed${NC}"
        return 1
    fi
}

# Function to backup logs
backup_logs() {
    echo -e "${BLUE}📝 Backing up logs...${NC}"
    
    # Create logs backup directory
    mkdir -p "$BACKUP_PATH/logs"
    
    # Copy all log files
    if [ -d "$PROJECT_ROOT/logs" ] && [ "$(ls -A "$PROJECT_ROOT/logs" 2>/dev/null)" ]; then
        cp -r "$PROJECT_ROOT/logs/"* "$BACKUP_PATH/logs/"
        echo -e "${GREEN}✅ Logs backup completed${NC}"
        echo "   Directory: $BACKUP_PATH/logs/"
        echo "   Files: $(ls "$BACKUP_PATH/logs/" | wc -l | tr -d ' ')"
    else
        echo -e "${YELLOW}⚠️  No logs found to backup${NC}"
        # Create empty logs directory to maintain structure
        touch "$BACKUP_PATH/logs/.gitkeep"
    fi
}

# Function to create backup metadata
create_metadata() {
    echo -e "${BLUE}📋 Creating backup metadata...${NC}"
    
    cat > "$BACKUP_PATH/backup_info.txt" << EOF
Backup Information
==================
Backup Name: $BACKUP_NAME
Created: $(date)
Project: Town Scryer
Database: $MYSQL_DATABASE
User: $MYSQL_USER

System Information:
- Docker Compose Version: $(docker-compose --version 2>/dev/null || echo "Not available")
- Docker Version: $(docker --version 2>/dev/null || echo "Not available")
- Host OS: $(uname -s)
- Host Architecture: $(uname -m)

Container Status at Backup Time:
$(docker-compose -f "$PROJECT_ROOT/docker-compose.yml" ps 2>/dev/null || echo "Could not retrieve container status")

Files in this backup:
$(find "$BACKUP_PATH" -type f -exec basename {} \; | sort)
EOF

    echo -e "${GREEN}✅ Metadata created${NC}"
}

# Function to create backup archive
create_archive() {
    echo -e "${BLUE}📦 Creating backup archive...${NC}"
    
    cd "$BACKUP_DIR"
    tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
    
    if [ $? -eq 0 ]; then
        # Remove uncompressed directory
        rm -rf "$BACKUP_NAME"
        
        echo -e "${GREEN}✅ Backup archive created${NC}"
        echo "   File: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
        echo "   Size: $(du -h "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" | cut -f1)"
    else
        echo -e "${RED}❌ Failed to create backup archive${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Database & Logs Backup${NC}"
    echo "=============================================="
    
    # Check if containers are running (with option to continue)
    check_containers
    
    # Perform backups
    backup_database || exit 1
    backup_logs
    create_metadata
    create_archive || exit 1
    
    echo ""
    echo -e "${GREEN}🎉 Backup completed successfully!${NC}"
    echo -e "${GREEN}Backup file: $BACKUP_DIR/${BACKUP_NAME}.tar.gz${NC}"
    echo ""
    echo "To restore this backup, use:"
    echo "  ./scripts/restore.sh ${BACKUP_NAME}.tar.gz"
    echo ""
    echo "Available backups:"
    ls -la "$BACKUP_DIR"/*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 " bytes, " $6 " " $7 " " $8 ")"}' || echo "  No previous backups found"
}

# Run main function
main "$@"
