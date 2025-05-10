#!/bin/bash
# Cryptobot Database Migration Script for Linux/macOS
# This script migrates database data from Docker volumes to local PostgreSQL

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

log "Starting database migration from Docker volumes to local PostgreSQL..."

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

# Backup local database before migration
log "Backing up local database before migration..."
BACKUP_FILE="$BACKUP_DIR/local_db_backup.sql"
if ! pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -f $BACKUP_FILE 2>/dev/null; then
    log "Warning: Failed to backup local database."
    log "Continuing with migration..."
else
    log "Local database backup created: $BACKUP_FILE"
fi

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

# Get Docker volume name
log "Identifying Docker volume for PostgreSQL data..."
if ! docker volume inspect postgres_data > /dev/null 2>&1; then
    log "Error: Could not find Docker volume 'postgres_data'. Please check your Docker setup."
    exit 1
fi

# Extract data from Docker container
log "Extracting database data from Docker container..."
TEMP_DIR="temp_postgres_data"
mkdir -p $TEMP_DIR

# Create a temporary container to access the volume
log "Creating temporary container to access volume data..."
TEMP_CONTAINER=$(docker run -d --rm -v postgres_data:/var/lib/postgresql/data --name temp_postgres_data alpine:latest tail -f /dev/null)
if [ $? -ne 0 ]; then
    log "Error: Failed to create temporary container."
    exit 1
fi

# Export database from Docker
log "Exporting database from Docker container..."
DOCKER_DB_BACKUP="$BACKUP_DIR/docker_db_backup.sql"
if ! docker exec cryptobot_postgres pg_dump -U cryptobot -d cryptobot > $DOCKER_DB_BACKUP 2>/dev/null; then
    log "Error: Failed to export database from Docker."
    
    # Try alternative approach with temporary container
    log "Trying alternative approach..."
    if ! docker exec temp_postgres_data sh -c "pg_dump -U cryptobot -d cryptobot" > $DOCKER_DB_BACKUP 2>/dev/null; then
        log "Error: Failed to export database using alternative approach."
        log "Cleaning up temporary container..."
        docker stop $TEMP_CONTAINER > /dev/null 2>&1
        exit 1
    fi
fi

# Clean up temporary container
log "Cleaning up temporary container..."
docker stop $TEMP_CONTAINER > /dev/null 2>&1

# Import data to local PostgreSQL
log "Importing data to local PostgreSQL..."
export PGPASSWORD=$DB_PASSWORD
if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $DOCKER_DB_BACKUP 2>/dev/null; then
    log "Error: Failed to import database to local PostgreSQL."
    log "Rolling back to previous state..."
    
    # Restore from backup
    if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $BACKUP_FILE 2>/dev/null; then
        log "Error: Failed to restore database from backup."
        log "Database may be in an inconsistent state. Please restore manually from backup: $BACKUP_FILE"
    else
        log "Database restored from backup."
    fi
    
    exit 1
fi

# Verify data migration
log "Verifying data migration..."
VERIFY_RESULT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM users;" -t 2>/dev/null)
if [ $? -ne 0 ]; then
    log "Warning: Verification query failed."
    log "Please verify the database manually."
else
    log "Verification successful. User count: $VERIFY_RESULT"
fi

# Clean up
log "Cleaning up temporary files..."
rm -rf $TEMP_DIR 2>/dev/null

log "Database migration completed successfully!"
log "Backup files are stored in: $BACKUP_DIR"
log "If you encounter any issues, you can restore from the backup using:"
log "psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $BACKUP_FILE"

exit 0