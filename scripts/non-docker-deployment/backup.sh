#!/bin/bash
#
# Backup script for Cryptobot non-Docker installation.
# This script creates a backup of the Cryptobot application, including configuration, database, and logs.
# It can be used for regular backups or before making significant changes to the system.
#
# Usage:
#   ./backup.sh [-n backup_name] [-l] [-d backup_dir]
#
# Options:
#   -n, --name        The name of the backup. If not provided, a timestamp will be used.
#   -l, --logs        Include logs in the backup. Default is false.
#   -d, --dir         The directory to store backups. Default is "backups" in the root directory.
#   -h, --help        Show this help message and exit.

# Exit on any error
set -e

# Script variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/backup_$TIMESTAMP.log"
INCLUDE_LOGS=false
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
    echo "Usage: $0 [-n backup_name] [-l] [-d backup_dir]"
    echo ""
    echo "Options:"
    echo "  -n, --name        The name of the backup. If not provided, a timestamp will be used."
    echo "  -l, --logs        Include logs in the backup. Default is false."
    echo "  -d, --dir         The directory to store backups. Default is 'backups' in the root directory."
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
            INCLUDE_LOGS=true
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

# Set backup name if not provided
if [ -z "$BACKUP_NAME" ]; then
    BACKUP_NAME="backup_$TIMESTAMP"
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Main backup process
{
    log "Starting backup process: $BACKUP_NAME"
    
    # Create backup directory
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    if [ -d "$BACKUP_PATH" ]; then
        log "Backup directory already exists: $BACKUP_PATH" "WARNING"
        read -p "Backup directory already exists. Do you want to overwrite it? (y/N) " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            log "Backup aborted by user" "WARNING"
            exit 0
        fi
        rm -rf "$BACKUP_PATH"
    fi
    
    mkdir -p "$BACKUP_PATH"
    log "Created backup directory: $BACKUP_PATH"
    
    # Stop services before backup
    stop_cryptobot_services
    
    # Use trap to ensure services are started even if the script fails
    trap start_cryptobot_services EXIT
    
    # 1. Backup configuration
    log "Backing up configuration"
    CONFIG_DIR="$ROOT_DIR/config"
    CONFIG_BACKUP_DIR="$BACKUP_PATH/config"
    
    if [ -d "$CONFIG_DIR" ]; then
        mkdir -p "$CONFIG_BACKUP_DIR"
        cp -R "$CONFIG_DIR"/* "$CONFIG_BACKUP_DIR"/
        log "Configuration backed up to: $CONFIG_BACKUP_DIR"
    else
        log "Configuration directory not found: $CONFIG_DIR" "WARNING"
    fi
    
    # 2. Backup database
    log "Backing up database"
    DB_BACKUP_DIR="$BACKUP_PATH/database"
    mkdir -p "$DB_BACKUP_DIR"
    
    # Check if PostgreSQL is installed
    if command_exists pg_dump; then
        log "PostgreSQL detected, using pg_dump"
        
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
        
        # Set PGPASSWORD environment variable for pg_dump
        export PGPASSWORD="$DB_PASSWORD"
        
        # Dump database
        DB_DUMP_FILE="$DB_BACKUP_DIR/$DB_NAME.sql"
        pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -F c -b -v -f "$DB_DUMP_FILE" "$DB_NAME"
        
        if [ $? -eq 0 ]; then
            log "Database backed up to: $DB_DUMP_FILE"
        else
            log "Database backup failed with exit code: $?" "ERROR"
        fi
        
        # Clear PGPASSWORD environment variable
        unset PGPASSWORD
    else
        # Check if SQLite is used
        SQLITE_DB_PATH="$ROOT_DIR/database/cryptobot.db"
        if [ -f "$SQLITE_DB_PATH" ]; then
            log "SQLite database detected, copying file"
            cp "$SQLITE_DB_PATH" "$DB_BACKUP_DIR/"
            log "SQLite database backed up to: $DB_BACKUP_DIR/cryptobot.db"
        else
            log "No database found, skipping database backup" "WARNING"
        fi
    fi
    
    # 3. Backup historical data
    log "Backing up historical data"
    DATA_DIR="$ROOT_DIR/data"
    DATA_BACKUP_DIR="$BACKUP_PATH/data"
    
    if [ -d "$DATA_DIR" ]; then
        mkdir -p "$DATA_BACKUP_DIR"
        cp -R "$DATA_DIR"/* "$DATA_BACKUP_DIR"/
        log "Historical data backed up to: $DATA_BACKUP_DIR"
    else
        log "Historical data directory not found: $DATA_DIR" "WARNING"
    fi
    
    # 4. Backup logs (optional)
    if [ "$INCLUDE_LOGS" = true ]; then
        log "Backing up logs"
        LOGS_BACKUP_DIR="$BACKUP_PATH/logs"
        
        if [ -d "$LOG_DIR" ]; then
            mkdir -p "$LOGS_BACKUP_DIR"
            cp -R "$LOG_DIR"/* "$LOGS_BACKUP_DIR"/
            log "Logs backed up to: $LOGS_BACKUP_DIR"
        else
            log "Logs directory not found: $LOG_DIR" "WARNING"
        fi
    fi
    
    # 5. Create backup metadata
    log "Creating backup metadata"
    METADATA_FILE="$BACKUP_PATH/metadata.json"
    
    cat > "$METADATA_FILE" << EOF
{
    "backupName": "$BACKUP_NAME",
    "timestamp": "$(date +"%Y-%m-%d %H:%M:%S")",
    "includeLogs": $INCLUDE_LOGS,
    "version": "1.0",
    "system": {
        "hostname": "$(hostname)",
        "os": "$(uname -s)",
        "kernel": "$(uname -r)",
        "architecture": "$(uname -m)"
    }
}
EOF
    
    log "Backup metadata created: $METADATA_FILE"
    
    # 6. Create backup archive
    log "Creating backup archive"
    BACKUP_ARCHIVE="$BACKUP_DIR/$BACKUP_NAME.tar.gz"
    
    if [ -f "$BACKUP_ARCHIVE" ]; then
        rm -f "$BACKUP_ARCHIVE"
    fi
    
    tar -czf "$BACKUP_ARCHIVE" -C "$BACKUP_PATH" .
    log "Backup archive created: $BACKUP_ARCHIVE"
    
    # 7. Clean up temporary backup directory
    rm -rf "$BACKUP_PATH"
    log "Temporary backup directory removed"
    
    log "Backup completed successfully: $BACKUP_NAME"
    
    # Start services after backup (this will also happen via the trap if the script fails)
    start_cryptobot_services
    
    # Remove the trap since we've manually started the services
    trap - EXIT
    
} || {
    error_message="$?"
    log "Backup failed: $error_message" "ERROR"
    
    # Services will be started by the trap
    exit 1
}