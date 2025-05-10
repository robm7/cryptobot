#!/bin/bash
#
# Restore script for Cryptobot non-Docker installation.
# This script restores a backup of the Cryptobot application, including configuration, database, and logs.
# It can be used to recover from failures or to roll back changes.
#
# Usage:
#   ./restore.sh -n backup_name [-l] [-d backup_dir]
#
# Options:
#   -n, --name        The name of the backup to restore. Required.
#   -l, --logs        Restore logs from the backup. Default is false.
#   -d, --dir         The directory where backups are stored. Default is "backups" in the root directory.
#   -h, --help        Show this help message and exit.

# Exit on any error
set -e

# Script variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/restore_$TIMESTAMP.log"
RESTORE_LOGS=false
BACKUP_NAME=""
BACKUP_DIR="$ROOT_DIR/backups"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log messages
log() {
    local level="INFO"
    if [ $# -eq 2 ]; then
        level="$2"
    fi
    
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    local message="[$timestamp] [$level] $1"
    
    # Write to console
    case "$level" in
        "INFO")
            echo -e "\033[0;32m$message\033[0m"
            ;;
        "WARNING")
            echo -e "\033[0;33m$message\033[0m"
            ;;
        "ERROR")
            echo -e "\033[0;31m$message\033[0m"
            ;;
        *)
            echo "$message"
            ;;
    esac
    
    # Write to log file
    echo "$message" >> "$LOG_FILE"
}

# Function to show help
show_help() {
    echo "Usage: $0 -n backup_name [-l] [-d backup_dir]"
    echo ""
    echo "Options:"
    echo "  -n, --name        The name of the backup to restore. Required."
    echo "  -l, --logs        Restore logs from the backup. Default is false."
    echo "  -d, --dir         The directory where backups are stored. Default is 'backups' in the root directory."
    echo "  -h, --help        Show this help message and exit."
    exit 0
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect the OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
    elif [ "$(uname)" == "Darwin" ]; then
        OS="macOS"
    else
        OS="Unknown"
    fi
    echo $OS
}

# Function to stop services
stop_cryptobot_services() {
    log "Stopping Cryptobot services"
    
    OS=$(detect_os)
    
    if [ "$OS" == "macOS" ]; then
        # macOS services using launchd
        for service in com.cryptobot.auth com.cryptobot.strategy com.cryptobot.backtest com.cryptobot.trade com.cryptobot.data; do
            if launchctl list | grep -q "$service"; then
                log "Stopping service: $service"
                sudo launchctl stop "$service"
            else
                log "Service not found: $service" "WARNING"
            fi
        done
    elif command_exists systemctl; then
        # Linux services using systemd
        for service in cryptobot-auth cryptobot-strategy cryptobot-backtest cryptobot-trade cryptobot-data; do
            if systemctl is-active --quiet "$service"; then
                log "Stopping service: $service"
                sudo systemctl stop "$service"
            else
                log "Service not found: $service" "WARNING"
            fi
        done
    else
        log "No service manager found (systemd or launchd), services must be stopped manually" "WARNING"
    fi
}

# Function to start services
start_cryptobot_services() {
    log "Starting Cryptobot services"
    
    OS=$(detect_os)
    
    if [ "$OS" == "macOS" ]; then
        # macOS services using launchd
        for service in com.cryptobot.auth com.cryptobot.strategy com.cryptobot.backtest com.cryptobot.trade com.cryptobot.data; do
            if launchctl list | grep -q "$service"; then
                log "Starting service: $service"
                sudo launchctl start "$service"
            else
                log "Service not found: $service" "WARNING"
            fi
        done
    elif command_exists systemctl; then
        # Linux services using systemd
        for service in cryptobot-auth cryptobot-strategy cryptobot-backtest cryptobot-trade cryptobot-data; do
            if systemctl is-enabled --quiet "$service" 2>/dev/null; then
                log "Starting service: $service"
                sudo systemctl start "$service"
            else
                log "Service not found: $service" "WARNING"
            fi
        done
    else
        log "No service manager found (systemd or launchd), services must be started manually" "WARNING"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            BACKUP_NAME="$2"
            shift 2
            ;;
        -l|--logs)
            RESTORE_LOGS=true
            shift
            ;;
        -d|--dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log "Unknown option: $1" "ERROR"
            show_help
            ;;
    esac
done

# Check if backup name is provided
if [ -z "$BACKUP_NAME" ]; then
    log "Backup name is required" "ERROR"
    show_help
fi

# Main restore process
{
    log "Starting restore process: $BACKUP_NAME"
    
    # Check if backup archive exists
    BACKUP_ARCHIVE="$BACKUP_DIR/$BACKUP_NAME.tar.gz"
    if [ ! -f "$BACKUP_ARCHIVE" ]; then
        log "Backup archive not found: $BACKUP_ARCHIVE" "ERROR"
        exit 1
    fi
    
    # Create temporary directory for extraction
    TEMP_DIR="/tmp/cryptobot_restore_$TIMESTAMP"
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
    
    mkdir -p "$TEMP_DIR"
    log "Created temporary directory: $TEMP_DIR"
    
    # Extract backup archive
    log "Extracting backup archive"
    tar -xzf "$BACKUP_ARCHIVE" -C "$TEMP_DIR"
    
    # Check if metadata file exists
    METADATA_FILE="$TEMP_DIR/metadata.json"
    if [ ! -f "$METADATA_FILE" ]; then
        log "Metadata file not found in backup: $METADATA_FILE" "ERROR"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Read metadata
    if command_exists jq; then
        BACKUP_TIMESTAMP=$(jq -r '.timestamp' "$METADATA_FILE")
        BACKUP_VERSION=$(jq -r '.version' "$METADATA_FILE")
        log "Backup metadata: Timestamp=$BACKUP_TIMESTAMP, Version=$BACKUP_VERSION"
    else
        log "jq not found, cannot parse metadata file" "WARNING"
        log "Metadata file content:"
        cat "$METADATA_FILE"
    fi
    
    # Stop services before restore
    stop_cryptobot_services
    
    # Use trap to ensure services are started even if the script fails
    trap start_cryptobot_services EXIT
    
    # Create backup of current state before restore
    log "Creating backup of current state before restore"
    PRE_RESTORE_BACKUP_NAME="pre_restore_$TIMESTAMP"
    BACKUP_SCRIPT="$SCRIPT_DIR/backup.sh"
    chmod +x "$BACKUP_SCRIPT"
    "$BACKUP_SCRIPT" -n "$PRE_RESTORE_BACKUP_NAME"
    
    if [ $? -ne 0 ]; then
        log "Pre-restore backup failed with exit code: $?" "WARNING"
        read -p "Pre-restore backup failed. Do you want to continue with the restore? (y/N) " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            log "Restore aborted by user" "WARNING"
            exit 0
        fi
    else
        log "Pre-restore backup created: $PRE_RESTORE_BACKUP_NAME"
    fi
    
    # 1. Restore configuration
    log "Restoring configuration"
    CONFIG_BACKUP_DIR="$TEMP_DIR/config"
    CONFIG_DIR="$ROOT_DIR/config"
    
    if [ -d "$CONFIG_BACKUP_DIR" ]; then
        # Backup current config
        CONFIG_BACKUP="/tmp/cryptobot_config_backup_$TIMESTAMP"
        if [ -d "$CONFIG_DIR" ]; then
            cp -R "$CONFIG_DIR" "$CONFIG_BACKUP"
            log "Current configuration backed up to: $CONFIG_BACKUP"
            
            # Clear current config
            rm -rf "$CONFIG_DIR"/*
        else
            mkdir -p "$CONFIG_DIR"
        fi
        
        # Restore config from backup
        cp -R "$CONFIG_BACKUP_DIR"/* "$CONFIG_DIR"/
        log "Configuration restored from backup"
    else
        log "Configuration not found in backup" "WARNING"
    fi
    
    # 2. Restore database
    log "Restoring database"
    DB_BACKUP_DIR="$TEMP_DIR/database"
    
    if [ -d "$DB_BACKUP_DIR" ]; then
        # Check if PostgreSQL is installed
        if command_exists pg_restore; then
            log "PostgreSQL detected, using pg_restore"
            
            # Get database connection info from environment or config
            DB_HOST=${CRYPTOBOT_DB_HOST:-localhost}
            DB_PORT=${CRYPTOBOT_DB_PORT:-5432}
            DB_USER=${CRYPTOBOT_DB_USER:-postgres}
            DB_NAME=${CRYPTOBOT_DB_NAME:-cryptobot}
            
            # Check if password is in environment
            if [ -z "$CRYPTOBOT_DB_PASSWORD" ]; then
                log "Database password not found in environment variables" "WARNING"
                read -s -p "Enter database password: " DB_PASSWORD
                echo
            else
                DB_PASSWORD="$CRYPTOBOT_DB_PASSWORD"
            fi
            
            # Set PGPASSWORD environment variable for pg_restore
            export PGPASSWORD="$DB_PASSWORD"
            
            # Find database dump file
            DB_DUMP_FILE="$DB_BACKUP_DIR/$DB_NAME.sql"
            if [ -f "$DB_DUMP_FILE" ]; then
                # Drop and recreate database
                log "Dropping and recreating database: $DB_NAME"
                
                # Use psql to drop and recreate database
                psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;"
                psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;"
                
                if [ $? -eq 0 ]; then
                    # Restore database
                    log "Restoring database from backup"
                    pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v "$DB_DUMP_FILE"
                    
                    if [ $? -eq 0 ]; then
                        log "Database restored successfully"
                    else
                        log "Database restore failed with exit code: $?" "ERROR"
                    fi
                else
                    log "Failed to recreate database with exit code: $?" "ERROR"
                fi
                
                # Clear PGPASSWORD environment variable
                unset PGPASSWORD
            else
                log "Database dump file not found in backup: $DB_DUMP_FILE" "WARNING"
            fi
        else
            # Check if SQLite is used
            SQLITE_DB_BACKUP="$DB_BACKUP_DIR/cryptobot.db"
            if [ -f "$SQLITE_DB_BACKUP" ]; then
                log "SQLite database detected, restoring file"
                
                SQLITE_DB_DIR="$ROOT_DIR/database"
                if [ ! -d "$SQLITE_DB_DIR" ]; then
                    mkdir -p "$SQLITE_DB_DIR"
                fi
                
                SQLITE_DB_PATH="$SQLITE_DB_DIR/cryptobot.db"
                
                # Backup current database
                if [ -f "$SQLITE_DB_PATH" ]; then
                    SQLITE_DB_BACKUP_PATH="/tmp/cryptobot_db_backup_$TIMESTAMP.db"
                    cp "$SQLITE_DB_PATH" "$SQLITE_DB_BACKUP_PATH"
                    log "Current SQLite database backed up to: $SQLITE_DB_BACKUP_PATH"
                fi
                
                # Restore database from backup
                cp "$SQLITE_DB_BACKUP" "$SQLITE_DB_PATH"
                log "SQLite database restored from backup"
            else
                log "No database found in backup" "WARNING"
            fi
        fi
    else
        log "Database not found in backup" "WARNING"
    fi
    
    # 3. Restore historical data
    log "Restoring historical data"
    DATA_BACKUP_DIR="$TEMP_DIR/data"
    DATA_DIR="$ROOT_DIR/data"
    
    if [ -d "$DATA_BACKUP_DIR" ]; then
        # Backup current data
        DATA_BACKUP="/tmp/cryptobot_data_backup_$TIMESTAMP"
        if [ -d "$DATA_DIR" ]; then
            cp -R "$DATA_DIR" "$DATA_BACKUP"
            log "Current historical data backed up to: $DATA_BACKUP"
            
            # Clear current data
            rm -rf "$DATA_DIR"/*
        else
            mkdir -p "$DATA_DIR"
        fi
        
        # Restore data from backup
        cp -R "$DATA_BACKUP_DIR"/* "$DATA_DIR"/
        log "Historical data restored from backup"
    else
        log "Historical data not found in backup" "WARNING"
    fi
    
    # 4. Restore logs (optional)
    if [ "$RESTORE_LOGS" = true ]; then
        log "Restoring logs"
        LOGS_BACKUP_DIR="$TEMP_DIR/logs"
        
        if [ -d "$LOGS_BACKUP_DIR" ]; then
            # Backup current logs
            LOGS_BACKUP="/tmp/cryptobot_logs_backup_$TIMESTAMP"
            if [ -d "$LOG_DIR" ]; then
                cp -R "$LOG_DIR" "$LOGS_BACKUP"
                log "Current logs backed up to: $LOGS_BACKUP"
                
                # Clear current logs
                rm -rf "$LOG_DIR"/*
            else
                mkdir -p "$LOG_DIR"
            fi
            
            # Restore logs from backup
            cp -R "$LOGS_BACKUP_DIR"/* "$LOG_DIR"/
            log "Logs restored from backup"
        else
            log "Logs not found in backup" "WARNING"
        fi
    fi
    
    log "Restore completed successfully: $BACKUP_NAME"
    
    # Clean up temporary directory
    rm -rf "$TEMP_DIR"
    log "Temporary directory removed"
    
    # Start services after restore (this will also happen via the trap if the script fails)
    start_cryptobot_services
    
    # Remove the trap since we've manually started the services
    trap - EXIT
    
} || {
    error_message="$?"
    log "Restore failed: $error_message" "ERROR"
    
    # Services will be started by the trap
    exit 1
}