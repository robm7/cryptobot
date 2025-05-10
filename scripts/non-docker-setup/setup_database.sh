#!/bin/bash
# Cryptobot PostgreSQL Database Setup Script for Linux/macOS
# This script installs and configures PostgreSQL for the Cryptobot application

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
    DB_HOST="localhost"
    DB_PORT="5432"
    DB_USER="cryptobot"
    DB_PASSWORD="changeme"
    DB_NAME="cryptobot"
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

# Install PostgreSQL based on OS
if [[ "$OS" == "linux" ]]; then
    log "Installing PostgreSQL for Linux..."
    
    # Detect package manager
    if command_exists apt-get; then
        log "Using apt package manager"
        sudo apt-get update
        sudo apt-get install -y postgresql postgresql-contrib
    elif command_exists yum; then
        log "Using yum package manager"
        sudo yum install -y postgresql-server postgresql-contrib
        sudo postgresql-setup --initdb
    elif command_exists dnf; then
        log "Using dnf package manager"
        sudo dnf install -y postgresql-server postgresql-contrib
        sudo postgresql-setup --initdb
    elif command_exists pacman; then
        log "Using pacman package manager"
        sudo pacman -Syu --noconfirm
        sudo pacman -S --noconfirm postgresql
        sudo -u postgres initdb -D /var/lib/postgres/data
    else
        log "Error: Unsupported package manager. Please install PostgreSQL manually."
        exit 1
    fi
    
    # Start PostgreSQL service
    if command_exists systemctl; then
        log "Starting PostgreSQL service using systemctl..."
        sudo systemctl enable postgresql
        sudo systemctl start postgresql
    elif command_exists service; then
        log "Starting PostgreSQL service using service command..."
        sudo service postgresql start
    else
        log "Error: Could not start PostgreSQL service. Please start it manually."
        exit 1
    fi
    
elif [[ "$OS" == "macos" ]]; then
    log "Installing PostgreSQL for macOS..."
    
    # Check if Homebrew is installed
    if ! command_exists brew; then
        log "Error: Homebrew is not installed. Please run setup_base_system.sh first."
        exit 1
    fi
    
    # Install PostgreSQL using Homebrew
    brew install postgresql
    
    # Start PostgreSQL service
    brew services start postgresql
fi

# Wait for PostgreSQL to start
log "Waiting for PostgreSQL to start..."
sleep 5

# Create database and user
log "Creating database and user..."
if [[ "$OS" == "linux" ]]; then
    # For Linux, use the postgres user to create the database and user
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" || log "User may already exist, continuing..."
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" || log "Database may already exist, continuing..."
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
elif [[ "$OS" == "macos" ]]; then
    # For macOS, use the current user to create the database and user
    createuser -s $DB_USER || log "User may already exist, continuing..."
    psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    createdb -O $DB_USER $DB_NAME || log "Database may already exist, continuing..."
fi

# Create database schema
log "Creating database schema..."
cat > db_schema.sql << EOL
-- Cryptobot Database Schema

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE
);

-- API Keys Table
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    exchange VARCHAR(50) NOT NULL,
    api_key VARCHAR(255) NOT NULL,
    api_secret VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id, exchange)
);

-- Strategies Table
CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id, name)
);

-- Trades Table
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE SET NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    order_id VARCHAR(100),
    order_type VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8),
    executed_price DECIMAL(18, 8),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP WITH TIME ZONE,
    profit_loss DECIMAL(18, 8)
);

-- Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);
EOL

# Apply database schema
if [[ "$OS" == "linux" ]]; then
    sudo -u postgres psql -d $DB_NAME -f db_schema.sql
elif [[ "$OS" == "macos" ]]; then
    psql -d $DB_NAME -f db_schema.sql
fi

# Clean up
rm db_schema.sql

log "PostgreSQL database setup completed successfully!"
log "Database: $DB_NAME"
log "User: $DB_USER"
log "Password: $DB_PASSWORD"
log "Host: $DB_HOST"
log "Port: $DB_PORT"

exit 0