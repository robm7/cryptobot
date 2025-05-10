#!/bin/bash
# Cryptobot Security Configuration Script for Linux/macOS
# This script applies security hardening configurations to the Cryptobot application

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
    REDIS_HOST="localhost"
    REDIS_PORT="6379"
    AUTH_SERVICE_PORT="8000"
    STRATEGY_SERVICE_PORT="8010"
    BACKTEST_SERVICE_PORT="8020"
    TRADE_SERVICE_PORT="8030"
    DATA_SERVICE_PORT="8001"
    LOG_LEVEL="INFO"
    LOG_DIR="./logs"
fi

log "Starting security configuration for Cryptobot..."

# Create security directory if it doesn't exist
mkdir -p config/security

# Generate strong random secret key for JWT tokens
log "Generating secure JWT secret key..."
JWT_SECRET=$(openssl rand -hex 32)
log "JWT secret key generated"

# Generate strong random secret key for password reset tokens
log "Generating secure password reset secret key..."
RESET_SECRET=$(openssl rand -hex 32)
log "Password reset secret key generated"

# Update .env file with secure keys
log "Updating environment configuration with secure keys..."
if grep -q "JWT_SECRET_KEY" .env; then
    # Replace existing JWT_SECRET_KEY
    sed -i.bak "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/" .env
else
    # Add JWT_SECRET_KEY
    echo "JWT_SECRET_KEY=$JWT_SECRET" >> .env
fi

if grep -q "RESET_SECRET_KEY" .env; then
    # Replace existing RESET_SECRET_KEY
    sed -i.bak "s/RESET_SECRET_KEY=.*/RESET_SECRET_KEY=$RESET_SECRET/" .env
else
    # Add RESET_SECRET_KEY
    echo "RESET_SECRET_KEY=$RESET_SECRET" >> .env
fi

# Configure secure Redis
log "Configuring secure Redis settings..."
if grep -q "REDIS_PASSWORD" .env; then
    # Check if Redis password is empty or weak
    REDIS_PWD=$(grep "REDIS_PASSWORD" .env | cut -d= -f2)
    if [ -z "$REDIS_PWD" ] || [ "$REDIS_PWD" == "changeme" ] || [ ${#REDIS_PWD} -lt 16 ]; then
        # Generate strong Redis password
        REDIS_PWD=$(openssl rand -hex 16)
        sed -i.bak "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$REDIS_PWD/" .env
        log "Generated strong Redis password"
    fi
else
    # Add Redis password
    REDIS_PWD=$(openssl rand -hex 16)
    echo "REDIS_PASSWORD=$REDIS_PWD" >> .env
    log "Added Redis password to environment configuration"
fi

# Configure secure database password
log "Configuring secure database settings..."
if grep -q "DB_PASSWORD" .env; then
    # Check if database password is weak
    DB_PWD=$(grep "DB_PASSWORD" .env | cut -d= -f2)
    if [ "$DB_PWD" == "changeme" ] || [ ${#DB_PWD} -lt 12 ]; then
        # Generate strong database password
        DB_PWD=$(openssl rand -base64 16 | tr -d '/+=' | cut -c1-16)
        sed -i.bak "s/DB_PASSWORD=.*/DB_PASSWORD=$DB_PWD/" .env
        log "Generated strong database password"
        
        # Update database user password
        if [[ "$OS" == "linux" ]]; then
            log "Updating PostgreSQL user password..."
            sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PWD';"
        elif [[ "$OS" == "macos" ]]; then
            log "Updating PostgreSQL user password..."
            psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PWD';"
        fi
    fi
fi

# Configure secure session settings
log "Configuring secure session settings..."
if grep -q "SESSION_EXPIRY" .env; then
    # Replace existing SESSION_EXPIRY
    sed -i.bak "s/SESSION_EXPIRY=.*/SESSION_EXPIRY=3600/" .env
else
    # Add SESSION_EXPIRY (1 hour)
    echo "SESSION_EXPIRY=3600" >> .env
fi

if grep -q "REFRESH_TOKEN_EXPIRY" .env; then
    # Replace existing REFRESH_TOKEN_EXPIRY
    sed -i.bak "s/REFRESH_TOKEN_EXPIRY=.*/REFRESH_TOKEN_EXPIRY=86400/" .env
else
    # Add REFRESH_TOKEN_EXPIRY (24 hours)
    echo "REFRESH_TOKEN_EXPIRY=86400" >> .env
fi

# Configure rate limiting
log "Configuring rate limiting..."
if grep -q "RATE_LIMIT_PER_MINUTE" .env; then
    # Replace existing RATE_LIMIT_PER_MINUTE
    sed -i.bak "s/RATE_LIMIT_PER_MINUTE=.*/RATE_LIMIT_PER_MINUTE=60/" .env
else
    # Add RATE_LIMIT_PER_MINUTE
    echo "RATE_LIMIT_PER_MINUTE=60" >> .env
fi

# Configure secure CORS settings
log "Configuring secure CORS settings..."
if grep -q "ALLOW_ORIGINS" .env; then
    # Replace existing ALLOW_ORIGINS with localhost only
    sed -i.bak "s/ALLOW_ORIGINS=.*/ALLOW_ORIGINS=http:\/\/localhost:3000,http:\/\/127.0.0.1:3000/" .env
else
    # Add ALLOW_ORIGINS
    echo "ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000" >> .env
fi

# Configure secure logging
log "Configuring secure logging..."
if grep -q "LOG_LEVEL" .env; then
    # Replace existing LOG_LEVEL
    sed -i.bak "s/LOG_LEVEL=.*/LOG_LEVEL=INFO/" .env
else
    # Add LOG_LEVEL
    echo "LOG_LEVEL=INFO" >> .env
fi

# Create security configuration file
log "Creating security configuration file..."
cat > config/security/security_config.json << EOL
{
    "security": {
        "password_policy": {
            "min_length": 12,
            "require_uppercase": true,
            "require_lowercase": true,
            "require_numbers": true,
            "require_special_chars": true,
            "max_age_days": 90,
            "prevent_reuse": 5
        },
        "session": {
            "expiry_seconds": 3600,
            "refresh_token_expiry_seconds": 86400,
            "idle_timeout_seconds": 1800,
            "max_sessions_per_user": 5
        },
        "rate_limiting": {
            "login_attempts_per_minute": 5,
            "api_requests_per_minute": 60,
            "api_key_requests_per_minute": 120
        },
        "mfa": {
            "required_for_admins": true,
            "required_for_api_key_creation": true,
            "totp_issuer": "Cryptobot"
        },
        "api_keys": {
            "rotation_days": 90,
            "max_keys_per_user": 5
        }
    }
}
EOL

# Create secure file permissions
log "Setting secure file permissions..."
chmod 600 .env
chmod 600 config/security/security_config.json

# Clean up backup files
rm -f .env.bak

log "Security configuration completed successfully!"
log "Note: You may need to restart services for some changes to take effect."
exit 0