#!/bin/bash
# Cryptobot Redis Setup Script for Linux/macOS
# This script installs and configures Redis for the Cryptobot application

set -e  # Exit immediately if a command exits with a non-zero status

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    log "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    log "Warning: .env file not found. Using default values."
    # Set default values
    REDIS_HOST="localhost"
    REDIS_PORT="6379"
    REDIS_PASSWORD=""
fi

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

# Install Redis based on OS
if [[ "$OS" == "linux" ]]; then
    log "Installing Redis for Linux..."
    
    # Detect package manager
    if command_exists apt-get; then
        log "Using apt package manager"
        sudo apt-get update
        sudo apt-get install -y redis-server
    elif command_exists yum; then
        log "Using yum package manager"
        sudo yum install -y redis
    elif command_exists dnf; then
        log "Using dnf package manager"
        sudo dnf install -y redis
    elif command_exists pacman; then
        log "Using pacman package manager"
        sudo pacman -Syu --noconfirm
        sudo pacman -S --noconfirm redis
    else
        log "Error: Unsupported package manager. Please install Redis manually."
        exit 1
    fi
    
    # Configure Redis
    log "Configuring Redis..."
    
    # Backup original configuration
    sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.bak
    
    # Update Redis configuration
    if [ -n "$REDIS_PASSWORD" ]; then
        log "Setting Redis password..."
        sudo sed -i "s/# requirepass foobared/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
    fi
    
    # Enable Redis to listen on all interfaces if needed
    sudo sed -i "s/bind 127.0.0.1/bind 0.0.0.0/" /etc/redis/redis.conf
    
    # Set Redis port
    sudo sed -i "s/port 6379/port $REDIS_PORT/" /etc/redis/redis.conf
    
    # Start Redis service
    if command_exists systemctl; then
        log "Starting Redis service using systemctl..."
        sudo systemctl enable redis
        sudo systemctl restart redis
    elif command_exists service; then
        log "Starting Redis service using service command..."
        sudo service redis restart
    else
        log "Error: Could not start Redis service. Please start it manually."
        exit 1
    fi
    
elif [[ "$OS" == "macos" ]]; then
    log "Installing Redis for macOS..."
    
    # Check if Homebrew is installed
    if ! command_exists brew; then
        log "Error: Homebrew is not installed. Please run setup_base_system.sh first."
        exit 1
    fi
    
    # Install Redis using Homebrew
    brew install redis
    
    # Configure Redis
    log "Configuring Redis..."
    
    # Backup original configuration
    cp $(brew --prefix)/etc/redis.conf $(brew --prefix)/etc/redis.conf.bak
    
    # Update Redis configuration
    if [ -n "$REDIS_PASSWORD" ]; then
        log "Setting Redis password..."
        sed -i '' "s/# requirepass foobared/requirepass $REDIS_PASSWORD/" $(brew --prefix)/etc/redis.conf
    fi
    
    # Set Redis port
    sed -i '' "s/port 6379/port $REDIS_PORT/" $(brew --prefix)/etc/redis.conf
    
    # Start Redis service
    brew services restart redis
fi

# Wait for Redis to start
log "Waiting for Redis to start..."
sleep 3

# Test Redis connection
log "Testing Redis connection..."
if command_exists redis-cli; then
    if [ -n "$REDIS_PASSWORD" ]; then
        redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping
    else
        redis-cli -h $REDIS_HOST -p $REDIS_PORT ping
    fi
    
    if [ $? -eq 0 ]; then
        log "Redis connection successful!"
    else
        log "Error: Could not connect to Redis. Please check your configuration."
        exit 1
    fi
else
    log "Warning: redis-cli not found. Could not test Redis connection."
fi

log "Redis setup completed successfully!"
log "Redis Host: $REDIS_HOST"
log "Redis Port: $REDIS_PORT"
if [ -n "$REDIS_PASSWORD" ]; then
    log "Redis Password: $REDIS_PASSWORD"
else
    log "Redis Password: Not set"
fi

exit 0