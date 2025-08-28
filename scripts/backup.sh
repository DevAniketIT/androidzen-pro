#!/bin/bash

# AndroidZen Pro - Database Backup Script
# Automated PostgreSQL database backup with rotation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BACKUP_DIR="/backups"
RETENTION_DAYS=7
MAX_BACKUPS=30
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$BACKUP_DIR/backup.log"

# Database configuration (from environment)
POSTGRES_HOST=${POSTGRES_HOST:-postgres}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-androidzen_user}
POSTGRES_DB=${POSTGRES_DB:-androidzen}

# Function to log messages
log_message() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

# Create backup directory if it doesn't exist
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_message "Created backup directory: $BACKUP_DIR"
    fi
}

# Check database connectivity
check_database() {
    log_message "Checking database connectivity..."
    
    if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB"; then
        log_success "Database is accessible"
    else
        log_error "Cannot connect to database"
        exit 1
    fi
}

# Create database backup
create_backup() {
    local backup_file="$BACKUP_DIR/androidzen_backup_$TIMESTAMP.sql"
    local backup_compressed="$backup_file.gz"
    
    log_message "Starting database backup..."
    log_message "Backup file: $backup_compressed"
    
    # Create the backup
    if pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --verbose \
        --no-owner \
        --no-privileges \
        --clean \
        --if-exists \
        > "$backup_file" 2>> "$LOG_FILE"; then
        
        # Compress the backup
        if gzip "$backup_file"; then
            local backup_size=$(du -h "$backup_compressed" | cut -f1)
            log_success "Backup created successfully: $backup_compressed ($backup_size)"
            
            # Verify backup integrity
            if gunzip -t "$backup_compressed" 2>/dev/null; then
                log_success "Backup integrity verified"
                echo "$backup_compressed" # Return backup file path
            else
                log_error "Backup integrity check failed"
                rm -f "$backup_compressed"
                exit 1
            fi
        else
            log_error "Failed to compress backup"
            rm -f "$backup_file"
            exit 1
        fi
    else
        log_error "Database backup failed"
        rm -f "$backup_file"
        exit 1
    fi
}

# Create schema-only backup
create_schema_backup() {
    local schema_file="$BACKUP_DIR/androidzen_schema_$TIMESTAMP.sql"
    
    log_message "Creating schema-only backup..."
    
    if pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --schema-only \
        --no-owner \
        --no-privileges \
        --clean \
        --if-exists \
        > "$schema_file" 2>> "$LOG_FILE"; then
        
        gzip "$schema_file"
        log_success "Schema backup created: ${schema_file}.gz"
    else
        log_warning "Schema backup failed"
        rm -f "$schema_file"
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log_message "Cleaning up old backups..."
    
    # Remove backups older than retention period
    if [ -d "$BACKUP_DIR" ]; then
        find "$BACKUP_DIR" -name "androidzen_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
        find "$BACKUP_DIR" -name "androidzen_schema_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
        
        # Ensure we don't exceed maximum backup count
        local backup_count=$(find "$BACKUP_DIR" -name "androidzen_backup_*.sql.gz" -type f | wc -l)
        
        if [ "$backup_count" -gt "$MAX_BACKUPS" ]; then
            local excess=$((backup_count - MAX_BACKUPS))
            log_warning "Backup count ($backup_count) exceeds maximum ($MAX_BACKUPS). Removing $excess oldest backups."
            
            find "$BACKUP_DIR" -name "androidzen_backup_*.sql.gz" -type f -printf '%T+ %p\n' | \
                sort | head -n "$excess" | cut -d' ' -f2- | xargs -r rm -f
        fi
        
        log_success "Cleanup completed"
    fi
}

# Generate backup report
generate_report() {
    local backup_file="$1"
    local report_file="$BACKUP_DIR/backup_report_$TIMESTAMP.txt"
    
    log_message "Generating backup report..."
    
    {
        echo "AndroidZen Pro Database Backup Report"
        echo "====================================="
        echo "Date: $(date)"
        echo "Backup File: $backup_file"
        echo "Database: $POSTGRES_DB"
        echo "Host: $POSTGRES_HOST"
        echo "Port: $POSTGRES_PORT"
        echo "User: $POSTGRES_USER"
        echo
        
        if [ -f "$backup_file" ]; then
            echo "Backup Details:"
            echo "  Size: $(du -h "$backup_file" | cut -f1)"
            echo "  Created: $(date -r "$backup_file")"
            echo "  MD5: $(md5sum "$backup_file" | cut -d' ' -f1)"
            echo
        fi
        
        echo "Current Backups:"
        find "$BACKUP_DIR" -name "androidzen_backup_*.sql.gz" -type f -printf '%TY-%Tm-%Td %TH:%TM  %s bytes  %p\n' | sort -r
        echo
        
        echo "Disk Usage:"
        df -h "$BACKUP_DIR"
        echo
        
        echo "Backup Statistics:"
        echo "  Total backups: $(find "$BACKUP_DIR" -name "androidzen_backup_*.sql.gz" -type f | wc -l)"
        echo "  Total size: $(du -sh "$BACKUP_DIR" | cut -f1)"
        
    } > "$report_file"
    
    log_success "Backup report generated: $report_file"
}

# Send notification (if configured)
send_notification() {
    local status="$1"
    local message="$2"
    
    # Email notification (if configured)
    if [ -n "$NOTIFICATION_EMAIL" ] && command -v mail >/dev/null 2>&1; then
        echo "$message" | mail -s "AndroidZen Pro Backup $status" "$NOTIFICATION_EMAIL"
        log_message "Email notification sent to $NOTIFICATION_EMAIL"
    fi
    
    # Webhook notification (if configured)
    if [ -n "$NOTIFICATION_WEBHOOK" ] && command -v curl >/dev/null 2>&1; then
        curl -X POST "$NOTIFICATION_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"status\":\"$status\",\"message\":\"$message\",\"timestamp\":\"$(date -Iseconds)\"}" \
            >/dev/null 2>&1
        log_message "Webhook notification sent"
    fi
}

# Main backup function
main() {
    log_message "Starting AndroidZen Pro database backup process..."
    
    # Initialize
    create_backup_dir
    check_database
    
    # Perform backup
    backup_file=$(create_backup)
    
    if [ -n "$backup_file" ]; then
        # Optional schema backup
        create_schema_backup
        
        # Cleanup old backups
        cleanup_old_backups
        
        # Generate report
        generate_report "$backup_file"
        
        # Send success notification
        send_notification "SUCCESS" "Database backup completed successfully: $backup_file"
        
        log_success "Backup process completed successfully"
        echo "$backup_file"  # Return backup file path for scripts
    else
        send_notification "FAILED" "Database backup failed"
        log_error "Backup process failed"
        exit 1
    fi
}

# Handle command line arguments
case "$1" in
    --help|-h)
        echo "AndroidZen Pro Database Backup Script"
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --test         Test database connectivity only"
        echo "  --cleanup      Cleanup old backups only"
        echo "  --restore FILE Restore database from backup file"
        echo
        echo "Environment Variables:"
        echo "  POSTGRES_HOST     Database host (default: postgres)"
        echo "  POSTGRES_PORT     Database port (default: 5432)"
        echo "  POSTGRES_USER     Database user (default: androidzen_user)"
        echo "  POSTGRES_DB       Database name (default: androidzen)"
        echo "  BACKUP_DIR        Backup directory (default: /backups)"
        echo "  RETENTION_DAYS    Days to keep backups (default: 7)"
        echo "  NOTIFICATION_EMAIL Email for notifications"
        echo "  NOTIFICATION_WEBHOOK Webhook URL for notifications"
        exit 0
        ;;
    --test)
        log_message "Testing database connectivity..."
        create_backup_dir
        check_database
        log_success "Database connectivity test passed"
        exit 0
        ;;
    --cleanup)
        log_message "Running cleanup only..."
        create_backup_dir
        cleanup_old_backups
        exit 0
        ;;
    --restore)
        if [ -z "$2" ]; then
            log_error "Please specify backup file to restore"
            exit 1
        fi
        
        backup_file="$2"
        if [ ! -f "$backup_file" ]; then
            log_error "Backup file not found: $backup_file"
            exit 1
        fi
        
        log_message "Restoring database from: $backup_file"
        log_warning "This will replace all data in the database. Continue? (y/N)"
        read -r confirm
        
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            if gunzip -c "$backup_file" | psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB"; then
                log_success "Database restored successfully"
            else
                log_error "Database restoration failed"
                exit 1
            fi
        else
            log_message "Restoration cancelled"
        fi
        exit 0
        ;;
    *)
        main
        ;;
esac
