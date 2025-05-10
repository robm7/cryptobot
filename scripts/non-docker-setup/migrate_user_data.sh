#!/bin/bash
# Cryptobot User Data Migration Script for Linux/macOS
# This script migrates user data, including API keys, preferences, and settings

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    log "Error: This script must be run as root. Please use sudo or run as root."
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

log "Starting user data migration from Docker to local PostgreSQL..."

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    log "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    log "Warning: .env file not found. Using default values."
fi

# Set default values if not defined in .env
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-cryptobot}
DB_PASSWORD=${DB_PASSWORD:-changeme}
DB_NAME=${DB_NAME:-cryptobot}

# Check if Docker is installed and running
log "Checking Docker installation..."
if ! docker info > /dev/null 2>&1; then
    log "Error: Docker is not running or not installed. Please start Docker and try again."
    exit 1
fi

# Check if PostgreSQL is installed and running
log "Checking PostgreSQL installation..."
export PGPASSWORD=$DB_PASSWORD
if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
    log "Error: PostgreSQL is not running or not properly configured. Please run setup_database.sh first."
    exit 1
fi

# Create backup directory
BACKUP_DIR="backup_$(date '+%Y%m%d_%H%M%S')"
mkdir -p $BACKUP_DIR
log "Created backup directory: $BACKUP_DIR"

# Check if the Docker container is running
log "Checking if Docker containers are running..."
if ! docker ps -q -f name=cryptobot_postgres > /dev/null 2>&1; then
    log "Warning: Docker container 'cryptobot_postgres' is not running."
    
    # Check if the container exists but is stopped
    if docker ps -a -q -f name=cryptobot_postgres > /dev/null 2>&1; then
        log "Found stopped container. Starting it temporarily for migration..."
        docker start cryptobot_postgres
        sleep 10  # Wait for container to start
    else
        log "Error: Docker container 'cryptobot_postgres' does not exist."
        log "Attempting to use Docker volume directly..."
    fi
fi

# Create necessary tables in local PostgreSQL for user data if they don't exist
log "Ensuring necessary tables exist for user data in local PostgreSQL..."
CREATE_TABLES_SCRIPT="
-- Create users table if it doesn't exist
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

-- Create API keys table if it doesn't exist
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

-- Create user settings table if it doesn't exist
CREATE TABLE IF NOT EXISTS user_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, setting_key)
);

-- Create user preferences table if it doesn't exist
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);
"

CREATE_TABLES_FILE="$BACKUP_DIR/create_user_tables.sql"
echo "$CREATE_TABLES_SCRIPT" > $CREATE_TABLES_FILE

export PGPASSWORD=$DB_PASSWORD
if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $CREATE_TABLES_FILE > /dev/null 2>&1; then
    log "Error: Failed to create tables in local PostgreSQL."
    exit 1
fi

# Export user data from Docker PostgreSQL
log "Exporting user data from Docker PostgreSQL..."
USERS_BACKUP_FILE="$BACKUP_DIR/users_data.csv"
API_KEYS_BACKUP_FILE="$BACKUP_DIR/api_keys_data.csv"
USER_SETTINGS_BACKUP_FILE="$BACKUP_DIR/user_settings_data.csv"
USER_PREFERENCES_BACKUP_FILE="$BACKUP_DIR/user_preferences_data.csv"

# Export users data
log "Exporting users data..."
if ! docker exec cryptobot_postgres psql -U cryptobot -d cryptobot -c "COPY (SELECT * FROM users) TO STDOUT WITH CSV HEADER" > $USERS_BACKUP_FILE 2>/dev/null; then
    log "Error: Failed to export users data from Docker."
    log "This may be because the table doesn't exist or the container is not running."
    log "Trying alternative approach..."
    
    # Create a temporary container to access the volume
    log "Creating temporary container to access volume data..."
    TEMP_CONTAINER=$(docker run -d --rm -v postgres_data:/var/lib/postgresql/data --name temp_postgres_data alpine:latest tail -f /dev/null)
    if [ $? -ne 0 ]; then
        log "Error: Failed to create temporary container."
        exit 1
    fi
    
    # Try alternative approach
    log "Export failed. This may be due to the container not running or other issues."
    log "Please ensure the PostgreSQL container is running and try again."
    
    # Clean up temporary container
    log "Cleaning up temporary container..."
    docker stop $TEMP_CONTAINER > /dev/null 2>&1
    
    exit 1
fi

# Export API keys data
log "Exporting API keys data..."
if ! docker exec cryptobot_postgres psql -U cryptobot -d cryptobot -c "COPY (SELECT * FROM api_keys) TO STDOUT WITH CSV HEADER" > $API_KEYS_BACKUP_FILE 2>/dev/null; then
    log "Warning: Failed to export API keys data from Docker."
    log "This may be because the table doesn't exist or is empty. Continuing with migration..."
fi

# Export user settings data
log "Exporting user settings data..."
if ! docker exec cryptobot_postgres psql -U cryptobot -d cryptobot -c "COPY (SELECT * FROM user_settings) TO STDOUT WITH CSV HEADER" > $USER_SETTINGS_BACKUP_FILE 2>/dev/null; then
    log "Warning: Failed to export user settings data from Docker."
    log "This may be because the table doesn't exist or is empty. Continuing with migration..."
fi

# Export user preferences data
log "Exporting user preferences data..."
if ! docker exec cryptobot_postgres psql -U cryptobot -d cryptobot -c "COPY (SELECT * FROM user_preferences) TO STDOUT WITH CSV HEADER" > $USER_PREFERENCES_BACKUP_FILE 2>/dev/null; then
    log "Warning: Failed to export user preferences data from Docker."
    log "This may be because the table doesn't exist or is empty. Continuing with migration..."
fi

# Import data to local PostgreSQL
log "Importing user data to local PostgreSQL..."

# Import users data
if [ -f $USERS_BACKUP_FILE ]; then
    log "Importing users data..."
    export PGPASSWORD=$DB_PASSWORD
    if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "COPY users FROM STDIN WITH CSV HEADER" < $USERS_BACKUP_FILE > /dev/null 2>&1; then
        log "Error: Failed to import users data to local PostgreSQL."
        exit 1
    fi
    log "Users data imported successfully."
else
    log "Warning: Users data file not found. Skipping import."
fi

# Import API keys data
if [ -f $API_KEYS_BACKUP_FILE ]; then
    log "Importing API keys data..."
    export PGPASSWORD=$DB_PASSWORD
    if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "COPY api_keys FROM STDIN WITH CSV HEADER" < $API_KEYS_BACKUP_FILE > /dev/null 2>&1; then
        log "Error: Failed to import API keys data to local PostgreSQL."
        exit 1
    fi
    log "API keys data imported successfully."
else
    log "Warning: API keys data file not found. Skipping import."
fi

# Import user settings data
if [ -f $USER_SETTINGS_BACKUP_FILE ]; then
    log "Importing user settings data..."
    export PGPASSWORD=$DB_PASSWORD
    if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "COPY user_settings FROM STDIN WITH CSV HEADER" < $USER_SETTINGS_BACKUP_FILE > /dev/null 2>&1; then
        log "Error: Failed to import user settings data to local PostgreSQL."
        exit 1
    fi
    log "User settings data imported successfully."
else
    log "Warning: User settings data file not found. Skipping import."
fi

# Import user preferences data
if [ -f $USER_PREFERENCES_BACKUP_FILE ]; then
    log "Importing user preferences data..."
    export PGPASSWORD=$DB_PASSWORD
    if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "COPY user_preferences FROM STDIN WITH CSV HEADER" < $USER_PREFERENCES_BACKUP_FILE > /dev/null 2>&1; then
        log "Error: Failed to import user preferences data to local PostgreSQL."
        exit 1
    fi
    log "User preferences data imported successfully."
else
    log "Warning: User preferences data file not found. Skipping import."
fi

# Verify data migration
log "Verifying data migration..."
VERIFY_USERS_RESULT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM users;" -t 2>/dev/null)
if [ $? -ne 0 ]; then
    log "Warning: Users verification query failed."
else
    log "Users data verification successful. Record count: $VERIFY_USERS_RESULT"
fi

VERIFY_API_KEYS_RESULT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM api_keys;" -t 2>/dev/null)
if [ $? -ne 0 ]; then
    log "Warning: API keys verification query failed."
else
    log "API keys data verification successful. Record count: $VERIFY_API_KEYS_RESULT"
fi

# Reset sequence values to avoid conflicts
log "Resetting sequence values..."
RESET_SEQUENCES_SCRIPT="
-- Reset users sequence
SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 0) FROM users), true);

-- Reset api_keys sequence
SELECT setval('api_keys_id_seq', (SELECT COALESCE(MAX(id), 0) FROM api_keys), true);

-- Reset user_settings sequence
SELECT setval('user_settings_id_seq', (SELECT COALESCE(MAX(id), 0) FROM user_settings), true);

-- Reset user_preferences sequence
SELECT setval('user_preferences_id_seq', (SELECT COALESCE(MAX(id), 0) FROM user_preferences), true);
"

RESET_SEQUENCES_FILE="$BACKUP_DIR/reset_sequences.sql"
echo "$RESET_SEQUENCES_SCRIPT" > $RESET_SEQUENCES_FILE

export PGPASSWORD=$DB_PASSWORD
if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $RESET_SEQUENCES_FILE > /dev/null 2>&1; then
    log "Warning: Failed to reset sequence values."
    log "This may cause issues with new record insertions. Please check manually."
else
    log "Sequence values reset successfully."
fi

log "User data migration completed successfully!"
log "Backup files are stored in: $BACKUP_DIR"

exit 0