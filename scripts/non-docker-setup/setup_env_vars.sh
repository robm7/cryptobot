#!/bin/bash
# Cryptobot Environment Variables Setup Script for Linux/macOS
# This script sets up environment variables for non-Docker deployment

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Create .env file in the project root
create_env_file() {
    local file_path="$1"
    shift
    local variables=("$@")
    
    if [ -f "$file_path" ]; then
        log "Backing up existing .env file to $file_path.bak"
        cp "$file_path" "$file_path.bak"
    fi
    
    log "Creating $file_path"
    > "$file_path"  # Clear or create file
    
    for var in "${variables[@]}"; do
        echo "$var" >> "$file_path"
    done
    
    log "Environment variables written to $file_path"
}

# Display welcome message
log "Setting up environment variables for Cryptobot services..."

# Get project root directory
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Common variables
common_vars=(
    "ENVIRONMENT=development"
    "DEBUG=true"
    "LOG_LEVEL=INFO"
)

# Create service-specific .env files
# Auth Service
auth_vars=(
    "${common_vars[@]}"
    "SERVER_HOST=0.0.0.0"
    "SERVER_PORT=8000"
    "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cryptobot_auth"
    "SECRET_KEY=dev_secret_key_change_in_production"
    "ACCESS_TOKEN_EXPIRE_MINUTES=30"
    "REFRESH_TOKEN_EXPIRE_DAYS=7"
)

create_env_file "$project_root/auth/.env" "${auth_vars[@]}"

# Strategy Service
strategy_vars=(
    "${common_vars[@]}"
    "SERVER_HOST=0.0.0.0"
    "SERVER_PORT=8000"
    "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cryptobot_strategy"
    "AUTH_SERVICE_URL=http://localhost:8000"
    "SECRET_KEY=dev_secret_key_change_in_production"
    "TOKEN_CACHE_TTL=60"
    "ADMIN_ROLE=admin"
    "TRADER_ROLE=trader"
    "VIEWER_ROLE=viewer"
)

create_env_file "$project_root/strategy/.env" "${strategy_vars[@]}"

# Trade Service
trade_vars=(
    "${common_vars[@]}"
    "SERVER_HOST=0.0.0.0"
    "SERVER_PORT=8000"
    "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cryptobot_trade"
    "AUTH_SERVICE_URL=http://localhost:8000"
    "TRADE_API_KEY=dev_trade_api_key_change_in_production"
    "EXCHANGE_API_KEY=your_exchange_api_key"
    "EXCHANGE_API_SECRET=your_exchange_api_secret"
    "EXCHANGE_PASSPHRASE="
    "EXCHANGE_SANDBOX=true"
)

create_env_file "$project_root/trade/.env" "${trade_vars[@]}"

# Backtest Service
backtest_vars=(
    "${common_vars[@]}"
    "SERVER_HOST=0.0.0.0"
    "SERVER_PORT=8000"
    "APP_NAME=Backtest Service"
    "MAX_CONCURRENT_BACKTESTS=5"
    "RESULTS_TTL_DAYS=7"
    "DATABASE_URL=sqlite:///./backtest.db"
    "DATA_SERVICE_URL=http://localhost:8001"
    "STRATEGY_SERVICE_URL=http://localhost:8000"
)

create_env_file "$project_root/backtest/.env" "${backtest_vars[@]}"

# Data Service
data_vars=(
    "${common_vars[@]}"
    "HOST=0.0.0.0"
    "PORT=8001"
    "WORKERS=1"
    "DATA_CACHE_TTL=300"
    "EXCHANGES=binance,kraken,coinbase"
    "REDIS_HOST=localhost"
    "REDIS_PORT=6379"
    "REDIS_DB=0"
    "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cryptobot_data"
)

create_env_file "$project_root/data/.env" "${data_vars[@]}"

# Create a global .env file in the project root
global_vars=(
    "ENVIRONMENT=development"
    "DEBUG=true"
    "LOG_LEVEL=INFO"
    "AUTH_SERVICE_URL=http://localhost:8000"
    "STRATEGY_SERVICE_URL=http://localhost:8000"
    "TRADE_SERVICE_URL=http://localhost:8000"
    "BACKTEST_SERVICE_URL=http://localhost:8000"
    "DATA_SERVICE_URL=http://localhost:8001"
)

create_env_file "$project_root/.env" "${global_vars[@]}"

log "Environment variables setup completed successfully!"
log "Note: For production use, please update the sensitive values in the .env files."

exit 0