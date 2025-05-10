#!/bin/bash
#
# Production deployment script for Cryptobot non-Docker installation.
# This script performs a complete production deployment of the Cryptobot application.
# It includes steps for backup, configuration, service deployment, and verification.

# Exit on any error
set -e

# Script variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_DIR="$ROOT_DIR/config/non-docker"
LOG_DIR="$ROOT_DIR/logs"
BACKUP_DIR="$ROOT_DIR/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/deployment_$TIMESTAMP.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

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

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run a script and check its exit code
run_script() {
    local script_path="$1"
    local description="$2"
    
    if [ ! -f "$script_path" ]; then
        log "Script not found: $script_path" "ERROR"
        exit 1
    fi
    
    log "Running: $description"
    
    # Make sure the script is executable
    chmod +x "$script_path"
    
    # Run the script
    "$script_path"
    
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log "Script failed with exit code $exit_code: $script_path" "ERROR"
        exit $exit_code
    fi
}

# Main deployment process
{
    log "Starting production deployment of Cryptobot"
    log "Deployment timestamp: $TIMESTAMP"
    
    # 1. Verify system requirements
    log "Verifying system requirements"
    requirements_script="$SCRIPT_DIR/../non-docker-setup/setup_base_system.sh"
    run_script "$requirements_script" "System requirements verification"
    
    # 2. Create backup before deployment
    log "Creating pre-deployment backup"
    backup_script="$SCRIPT_DIR/backup.sh"
    backup_name="pre_deployment_$TIMESTAMP"
    chmod +x "$backup_script"
    "$backup_script" -n "$backup_name"
    
    if [ $? -ne 0 ]; then
        log "Backup failed with exit code $?" "ERROR"
        exit 1
    fi
    
    # 3. Stop all services
    log "Stopping all services"
    stop_script="$ROOT_DIR/scripts/non-docker-setup/stop_all.sh"
    if [ -f "$stop_script" ]; then
        run_script "$stop_script" "Stopping all services"
    else
        log "Stop script not found, attempting to stop services manually" "WARNING"
        
        # Check for systemd
        if command_exists systemctl; then
            systemctl stop 'cryptobot-*' 2>/dev/null || true
        # Check for launchd (macOS)
        elif command_exists launchctl; then
            launchctl list | grep 'com.cryptobot.' | awk '{print $3}' | xargs -I{} launchctl stop {} 2>/dev/null || true
        else
            log "Could not determine service manager, manual intervention may be required" "WARNING"
        fi
    fi
    
    # 4. Update configuration
    log "Updating configuration"
    config_script="$SCRIPT_DIR/../non-docker-setup/config_migration.sh"
    run_script "$config_script" "Configuration update"
    
    # 5. Apply security hardening
    log "Applying security hardening"
    security_script="$SCRIPT_DIR/../non-docker-security/secure_config.sh"
    run_script "$security_script" "Security hardening"
    
    # 6. Update services
    log "Updating services"
    services_script="$SCRIPT_DIR/../non-docker-setup/install_services.sh"
    run_script "$services_script" "Services update"
    
    # 7. Set up monitoring
    log "Setting up monitoring"
    monitoring_script="$SCRIPT_DIR/setup_monitoring.sh"
    run_script "$monitoring_script" "Monitoring setup"
    
    # 8. Set up logging
    log "Setting up logging"
    logging_script="$SCRIPT_DIR/setup_logging.sh"
    run_script "$logging_script" "Logging setup"
    
    # 9. Set up alerting
    log "Setting up alerting"
    alerting_script="$SCRIPT_DIR/setup_alerts.sh"
    run_script "$alerting_script" "Alerting setup"
    
    # 10. Start all services
    log "Starting all services"
    start_script="$ROOT_DIR/scripts/non-docker-setup/start_all.sh"
    run_script "$start_script" "Starting all services"
    
    # 11. Run verification tests
    log "Running verification tests"
    test_script="$ROOT_DIR/scripts/non-docker-tests/run_all_tests.sh"
    run_script "$test_script" "Verification tests"
    
    # 12. Verify monitoring is working
    log "Verifying monitoring"
    monitoring_verify_script="$SCRIPT_DIR/verify_monitoring.sh"
    if [ -f "$monitoring_verify_script" ]; then
        run_script "$monitoring_verify_script" "Monitoring verification"
    else
        log "Monitoring verification script not found, skipping" "WARNING"
    fi
    
    log "Deployment completed successfully"
    
} || {
    error_message="$?"
    log "Deployment failed: $error_message" "ERROR"
    
    # Attempt to restore from backup
    log "Attempting to restore from backup" "WARNING"
    restore_script="$SCRIPT_DIR/restore.sh"
    chmod +x "$restore_script"
    "$restore_script" -n "$backup_name"
    
    exit 1
}