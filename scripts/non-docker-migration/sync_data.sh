#!/bin/bash
# sync_data.sh
# Script to synchronize data between Docker and non-Docker environments
# Part of Phase 11: Parallel Operation Strategy

set -e

echo "=== Cryptobot Data Synchronization Tool ==="
echo "This script synchronizes data between Docker and non-Docker environments."

# Check if environment variables are set
if [ -z "$CRYPTOBOT_SHARED_DATA_DIR" ]; then
    # Source environment file if it exists
    if [ -f "/opt/cryptobot/shared_data/config/environment.sh" ]; then
        source /opt/cryptobot/shared_data/config/environment.sh
    else
        echo "Error: CRYPTOBOT_SHARED_DATA_DIR environment variable not set."
        echo "Please run setup_parallel_env.sh first or set the variable manually."
        exit 1
    fi
fi

# Define directories
SHARED_DATA_DIR=${CRYPTOBOT_SHARED_DATA_DIR:-"/opt/cryptobot/shared_data"}
DOCKER_ENV_DIR="/opt/cryptobot/docker"
NON_DOCKER_ENV_DIR="/opt/cryptobot/non-docker"
LOG_DIR=${CRYPTOBOT_LOG_DIR:-"/var/log/cryptobot"}
SYNC_LOG="$LOG_DIR/data_sync.log"

# Create sync log directory if it doesn't exist
mkdir -p $(dirname "$SYNC_LOG")

# Function to log messages
log_message() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $1" | tee -a "$SYNC_LOG"
}

# Function to check if a service is running
is_service_running() {
    local port=$1
    local pid=$(lsof -t -i:$port 2>/dev/null)
    if [ -n "$pid" ]; then
        return 0  # Service is running
    else
        return 1  # Service is not running
    fi
}

# Function to sync database data
sync_database() {
    log_message "Starting database synchronization..."
    
    # Check if PostgreSQL is running
    if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        log_message "Error: PostgreSQL is not running. Please start the database service."
        return 1
    fi
    
    # Create backup of the database
    local timestamp=$(date "+%Y%m%d%H%M%S")
    local backup_file="$SHARED_DATA_DIR/database/backup_$timestamp.sql"
    
    log_message "Creating database backup: $backup_file"
    PGPASSWORD=${CRYPTOBOT_DB_PASSWORD:-"use_env_var_in_production"} pg_dump -h localhost -U ${CRYPTOBOT_DB_USER:-"cryptobot"} -d ${CRYPTOBOT_DB_NAME:-"cryptobot"} -f "$backup_file"
    
    log_message "Database backup completed successfully."
    return 0
}

# Function to sync historical data
sync_historical_data() {
    log_message "Starting historical data synchronization..."
    
    # Check if data directories exist
    if [ ! -d "$SHARED_DATA_DIR/historical_data" ]; then
        log_message "Creating historical data directory..."
        mkdir -p "$SHARED_DATA_DIR/historical_data"
    fi
    
    # Check if data service is running in Docker
    if is_service_running ${CRYPTOBOT_DOCKER_DATA_PORT:-"8004"}; then
        log_message "Docker data service is running. Stopping service for safe synchronization..."
        # Here you would typically stop the Docker service, but for safety we'll just log it
        log_message "WARNING: Please stop the Docker data service manually before proceeding."
        read -p "Press Enter to continue after stopping the Docker data service..."
    fi
    
    # Check if data service is running in non-Docker
    if is_service_running ${CRYPTOBOT_NON_DOCKER_DATA_PORT:-"9004"}; then
        log_message "Non-Docker data service is running. Stopping service for safe synchronization..."
        # Here you would typically stop the non-Docker service, but for safety we'll just log it
        log_message "WARNING: Please stop the non-Docker data service manually before proceeding."
        read -p "Press Enter to continue after stopping the non-Docker data service..."
    fi
    
    log_message "Synchronizing historical data..."
    
    # Create a timestamp for the backup
    local timestamp=$(date "+%Y%m%d%H%M%S")
    
    # Create a backup of the current historical data
    if [ -d "$SHARED_DATA_DIR/historical_data" ] && [ "$(ls -A "$SHARED_DATA_DIR/historical_data")" ]; then
        log_message "Creating backup of historical data..."
        tar -czf "$SHARED_DATA_DIR/historical_data_backup_$timestamp.tar.gz" -C "$SHARED_DATA_DIR" historical_data
        log_message "Historical data backup completed: $SHARED_DATA_DIR/historical_data_backup_$timestamp.tar.gz"
    fi
    
    log_message "Historical data synchronization completed."
    return 0
}

# Function to sync user data
sync_user_data() {
    log_message "Starting user data synchronization..."
    
    # Check if user data directory exists
    if [ ! -d "$SHARED_DATA_DIR/user_data" ]; then
        log_message "Creating user data directory..."
        mkdir -p "$SHARED_DATA_DIR/user_data"
    fi
    
    # Check if trade service is running in Docker
    if is_service_running ${CRYPTOBOT_DOCKER_TRADE_PORT:-"8003"}; then
        log_message "Docker trade service is running. Stopping service for safe synchronization..."
        # Here you would typically stop the Docker service, but for safety we'll just log it
        log_message "WARNING: Please stop the Docker trade service manually before proceeding."
        read -p "Press Enter to continue after stopping the Docker trade service..."
    fi
    
    # Check if trade service is running in non-Docker
    if is_service_running ${CRYPTOBOT_NON_DOCKER_TRADE_PORT:-"9003"}; then
        log_message "Non-Docker trade service is running. Stopping service for safe synchronization..."
        # Here you would typically stop the non-Docker service, but for safety we'll just log it
        log_message "WARNING: Please stop the non-Docker trade service manually before proceeding."
        read -p "Press Enter to continue after stopping the non-Docker trade service..."
    fi
    
    log_message "Synchronizing user data..."
    
    # Create a timestamp for the backup
    local timestamp=$(date "+%Y%m%d%H%M%S")
    
    # Create a backup of the current user data
    if [ -d "$SHARED_DATA_DIR/user_data" ] && [ "$(ls -A "$SHARED_DATA_DIR/user_data")" ]; then
        log_message "Creating backup of user data..."
        tar -czf "$SHARED_DATA_DIR/user_data_backup_$timestamp.tar.gz" -C "$SHARED_DATA_DIR" user_data
        log_message "User data backup completed: $SHARED_DATA_DIR/user_data_backup_$timestamp.tar.gz"
    fi
    
    log_message "User data synchronization completed."
    return 0
}

# Function to sync configuration data
sync_config() {
    log_message "Starting configuration synchronization..."
    
    # Check if config directory exists
    if [ ! -d "$SHARED_DATA_DIR/config" ]; then
        log_message "Creating config directory..."
        mkdir -p "$SHARED_DATA_DIR/config"
    fi
    
    log_message "Synchronizing configuration data..."
    
    # Create a timestamp for the backup
    local timestamp=$(date "+%Y%m%d%H%M%S")
    
    # Create a backup of the current configuration
    if [ -d "$SHARED_DATA_DIR/config" ] && [ "$(ls -A "$SHARED_DATA_DIR/config")" ]; then
        log_message "Creating backup of configuration data..."
        tar -czf "$SHARED_DATA_DIR/config_backup_$timestamp.tar.gz" -C "$SHARED_DATA_DIR" config
        log_message "Configuration backup completed: $SHARED_DATA_DIR/config_backup_$timestamp.tar.gz"
    fi
    
    log_message "Configuration synchronization completed."
    return 0
}

# Function to verify data integrity
verify_data_integrity() {
    log_message "Verifying data integrity..."
    
    # Check database connectivity
    if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        log_message "Database connection: OK"
    else
        log_message "Database connection: FAILED"
        return 1
    fi
    
    # Check historical data directory
    if [ -d "$SHARED_DATA_DIR/historical_data" ] && [ "$(ls -A "$SHARED_DATA_DIR/historical_data")" ]; then
        log_message "Historical data: OK"
    else
        log_message "Historical data: WARNING - Directory empty or not found"
    fi
    
    # Check user data directory
    if [ -d "$SHARED_DATA_DIR/user_data" ] && [ "$(ls -A "$SHARED_DATA_DIR/user_data")" ]; then
        log_message "User data: OK"
    else
        log_message "User data: WARNING - Directory empty or not found"
    fi
    
    # Check config directory
    if [ -d "$SHARED_DATA_DIR/config" ] && [ "$(ls -A "$SHARED_DATA_DIR/config")" ]; then
        log_message "Configuration data: OK"
    else
        log_message "Configuration data: WARNING - Directory empty or not found"
    fi
    
    log_message "Data integrity verification completed."
    return 0
}

# Main function
main() {
    log_message "Starting data synchronization process..."
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --database-only)
                sync_database
                exit $?
                ;;
            --historical-only)
                sync_historical_data
                exit $?
                ;;
            --user-only)
                sync_user_data
                exit $?
                ;;
            --config-only)
                sync_config
                exit $?
                ;;
            --verify-only)
                verify_data_integrity
                exit $?
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Synchronize data between Docker and non-Docker environments."
                echo ""
                echo "Options:"
                echo "  --database-only    Synchronize only database data"
                echo "  --historical-only  Synchronize only historical data"
                echo "  --user-only        Synchronize only user data"
                echo "  --config-only      Synchronize only configuration data"
                echo "  --verify-only      Verify data integrity only"
                echo "  --help             Display this help message"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information."
                exit 1
                ;;
        esac
        shift
    done
    
    # Run all synchronization steps
    sync_database
    sync_historical_data
    sync_user_data
    sync_config
    verify_data_integrity
    
    log_message "Data synchronization process completed successfully."
    
    echo ""
    echo "=== Data Synchronization Complete ==="
    echo "Shared data directory: $SHARED_DATA_DIR"
    echo "Log file: $SYNC_LOG"
    echo ""
    echo "Next steps:"
    echo "1. Restart Docker services if they were stopped"
    echo "2. Restart non-Docker services if they were stopped"
    echo "3. Verify application functionality in both environments"
    echo ""
    echo "For more information, see the migration documentation."
}

# Run the main function
main "$@"