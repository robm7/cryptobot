#!/bin/bash
# Cryptobot Master Environment Setup Script for Linux/macOS
# This script orchestrates the entire environment setup process

set -e  # Exit immediately if a command exits with a non-zero status

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    log "Detected Linux operating system"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    log "Detected macOS operating system"
else
    log "Error: Unsupported operating system. This script is for Linux and macOS only."
    exit 1
fi

# Check if running as root/sudo
if [ "$EUID" -ne 0 ]; then
    log "Warning: This script may require sudo privileges for some operations."
    log "If you encounter permission errors, please run with sudo."
    read -p "Continue without sudo? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Please run the script with sudo."
        exit 1
    fi
fi

# Display welcome message
log "Welcome to the Cryptobot Environment Setup!"
log "This script will set up the complete environment for the Cryptobot application."
log "The setup process includes:"
log "1. Base system preparation"
log "2. PostgreSQL database installation and configuration"
log "3. Redis installation and configuration"
log "4. Python environment setup"
log ""
log "The setup process may take several minutes to complete."
log ""

read -p "Press Enter to continue or Ctrl+C to cancel..."

# Create a directory for logs
mkdir -p logs

# Step 1: Base system preparation
log "Step 1: Base system preparation"
log "Running setup_base_system.sh..."
bash ./scripts/non-docker-setup/setup_base_system.sh 2>&1 | tee logs/setup_base_system.log

if [ $? -ne 0 ]; then
    log "Error: Base system setup failed. Please check logs/setup_base_system.log for details."
    exit 1
fi

log "Base system setup completed successfully!"

# Step 2: PostgreSQL database installation and configuration
log "Step 2: PostgreSQL database installation and configuration"
log "Running setup_database.sh..."
bash ./scripts/non-docker-setup/setup_database.sh 2>&1 | tee logs/setup_database.log

if [ $? -ne 0 ]; then
    log "Error: Database setup failed. Please check logs/setup_database.log for details."
    exit 1
fi

log "Database setup completed successfully!"

# Step 3: Redis installation and configuration
log "Step 3: Redis installation and configuration"
log "Running setup_redis.sh..."
bash ./scripts/non-docker-setup/setup_redis.sh 2>&1 | tee logs/setup_redis.log

if [ $? -ne 0 ]; then
    log "Error: Redis setup failed. Please check logs/setup_redis.log for details."
    exit 1
fi

log "Redis setup completed successfully!"

# Step 4: Python environment setup
log "Step 4: Python environment setup"
log "Running setup_python_env.sh..."
bash ./scripts/non-docker-setup/setup_python_env.sh 2>&1 | tee logs/setup_python_env.log

if [ $? -ne 0 ]; then
    log "Error: Python environment setup failed. Please check logs/setup_python_env.log for details."
    exit 1
fi

log "Python environment setup completed successfully!"

# Final steps and verification
log "Verifying installation..."

# Check if PostgreSQL is running
if command_exists pg_isready; then
    pg_isready
    if [ $? -eq 0 ]; then
        log "PostgreSQL is running correctly."
    else
        log "Warning: PostgreSQL may not be running correctly."
    fi
else
    log "Warning: pg_isready command not found. Could not verify PostgreSQL status."
fi

# Check if Redis is running
if command_exists redis-cli; then
    redis-cli ping
    if [ $? -eq 0 ]; then
        log "Redis is running correctly."
    else
        log "Warning: Redis may not be running correctly."
    fi
else
    log "Warning: redis-cli command not found. Could not verify Redis status."
fi

# Check if Python virtual environment was created
if [ -d "venv" ]; then
    log "Python virtual environment is set up correctly."
else
    log "Warning: Python virtual environment may not be set up correctly."
fi

log "Environment setup completed successfully!"
log ""
log "To activate the Python virtual environment, run:"
log "  source ./activate_env.sh"
log ""
log "To start the Cryptobot application, run:"
log "  ./run_cryptobot.sh"
log ""
log "Thank you for installing Cryptobot!"

exit 0