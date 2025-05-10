#!/bin/bash
# Cryptobot Configuration Migration Script for Linux/macOS
# This script orchestrates the entire configuration migration process

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    log "Warning: Some operations may require root privileges."
fi

# Display welcome message
log "Welcome to the Cryptobot Configuration Migration!"
log "This script will migrate Docker configurations to non-Docker configurations."
log "The migration process includes:"
log "1. Creating template configuration files"
log "2. Setting up environment variables"
log "3. Generating service-specific configurations"
log ""
log "The migration process may take several minutes to complete."
log ""

read -p "Press Enter to continue or Ctrl+C to cancel..."

# Get project root directory
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Create a directory for logs
mkdir -p "$project_root/logs"

# Step 1: Run the configuration migration utility
log "Step 1: Running configuration migration utility..."
log "Running migrate_config.py..."

python_path="python3"
migrate_config_path="$project_root/scripts/non-docker-setup/migrate_config.py"

# Make the script executable
chmod +x "$migrate_config_path"

# Run the migration utility
$python_path "$migrate_config_path" --project-root "$project_root" 2>&1 | tee "$project_root/logs/migrate_config.log"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    log "Error: Configuration migration failed. Please check logs/migrate_config.log for details."
    exit 1
fi

log "Configuration migration completed successfully!"

# Step 2: Set up environment variables
log "Step 2: Setting up environment variables..."
log "Running setup_env_vars.sh..."

env_vars_script="$project_root/scripts/non-docker-setup/setup_env_vars.sh"

# Make the script executable
chmod +x "$env_vars_script"

# Run the environment variables setup script
"$env_vars_script" 2>&1 | tee "$project_root/logs/setup_env_vars.log"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    log "Error: Environment variables setup failed. Please check logs/setup_env_vars.log for details."
    exit 1
fi

log "Environment variables setup completed successfully!"

# Step 3: Generate service-specific configurations
log "Step 3: Generating service-specific configurations..."
log "Running generate_service_configs.sh..."

service_configs_script="$project_root/scripts/non-docker-setup/generate_service_configs.sh"

# Make the script executable
chmod +x "$service_configs_script"

# Run the service configuration generation script
"$service_configs_script" 2>&1 | tee "$project_root/logs/generate_service_configs.log"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    log "Error: Service configuration generation failed. Please check logs/generate_service_configs.log for details."
    exit 1
fi

log "Service configuration generation completed successfully!"

# Final steps and verification
log "Verifying configuration files..."

# Check if configuration files were created
services=("auth" "strategy" "trade" "backtest" "data")
all_configs_created=true

for service in "${services[@]}"; do
    config_path="$project_root/$service/config.yaml"
    env_path="$project_root/$service/.env"
    
    if [ ! -f "$config_path" ]; then
        log "Warning: Configuration file not found for $service service: $config_path"
        all_configs_created=false
    fi
    
    if [ ! -f "$env_path" ]; then
        log "Warning: Environment file not found for $service service: $env_path"
        all_configs_created=false
    fi
done

if $all_configs_created; then
    log "All configuration files were created successfully."
else
    log "Warning: Some configuration files may be missing."
fi

log "Configuration migration completed successfully!"
log ""
log "The following files have been created:"
log "1. Template configuration files in config/non-docker/"
log "2. Environment variable files (.env) in each service directory"
log "3. Service-specific configuration files (config.yaml) in each service directory"
log ""
log "To start the services with the new configuration:"
log "1. Activate the Python virtual environment"
log "2. Run each service with the new configuration"
log ""
log "Thank you for using the Cryptobot Configuration Migration Utility!"

exit 0