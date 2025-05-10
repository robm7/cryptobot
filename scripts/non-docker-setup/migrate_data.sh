#!/bin/bash
# Cryptobot Master Data Migration Script for Linux/macOS
# This script orchestrates the execution of all data migration scripts

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

# Display welcome message
log "Welcome to the Cryptobot Data Migration Tool!"
log "This script will migrate all data from Docker volumes to the local PostgreSQL installation."
log "The migration process includes:"
log "1. Database migration (users, strategies, trades, etc.)"
log "2. Historical market data migration"
log "3. User data migration (API keys, preferences, settings)"
log ""
log "The migration process may take several minutes to complete, depending on the amount of data."
log "Please ensure that Docker is running and the PostgreSQL service is installed and running."
log ""

read -p "Press Enter to continue or Ctrl+C to cancel..."

# Create a master log file
LOG_FILE="logs/data_migration_$(date '+%Y%m%d_%H%M%S').log"
exec > >(tee -a "$LOG_FILE") 2>&1

# Step 1: Database Migration
log "Step 1: Database Migration"
log "Running migrate_database.sh..."
if ! bash "$PWD/scripts/non-docker-setup/migrate_database.sh"; then
    log "Error: Database migration failed. Please check logs for details."
    exit 1
fi

log "Database migration completed successfully!"

# Step 2: Historical Data Migration
log "Step 2: Historical Data Migration"
log "Running migrate_historical_data.sh..."
if ! bash "$PWD/scripts/non-docker-setup/migrate_historical_data.sh"; then
    log "Error: Historical data migration failed. Please check logs for details."
    exit 1
fi

log "Historical data migration completed successfully!"

# Step 3: User Data Migration
log "Step 3: User Data Migration"
log "Running migrate_user_data.sh..."
if ! bash "$PWD/scripts/non-docker-setup/migrate_user_data.sh"; then
    log "Error: User data migration failed. Please check logs for details."
    exit 1
fi

log "User data migration completed successfully!"

# Step 4: Verify Data Integrity
log "Step 4: Verifying Data Integrity"
log "Running data verification checks..."

# Create verification script
VERIFICATION_SCRIPT="
-- Verification queries
SELECT 'Users Count: ' || COUNT(*) FROM users;
SELECT 'API Keys Count: ' || COUNT(*) FROM api_keys;
SELECT 'Strategies Count: ' || COUNT(*) FROM strategies;
SELECT 'Trades Count: ' || COUNT(*) FROM trades;
SELECT 'OHLCV Data Count: ' || COUNT(*) FROM ohlcv;
SELECT 'Backtest Results Count: ' || COUNT(*) FROM backtest_results;

-- Check for orphaned records
SELECT 'Orphaned API Keys: ' || COUNT(*) 
FROM api_keys ak 
WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = ak.user_id);

SELECT 'Orphaned Strategies: ' || COUNT(*) 
FROM strategies s 
WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = s.user_id);

SELECT 'Orphaned Trades: ' || COUNT(*) 
FROM trades t 
WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = t.user_id);

-- Check for data consistency
SELECT 'Users with API Keys: ' || COUNT(DISTINCT user_id) FROM api_keys;
SELECT 'Users with Strategies: ' || COUNT(DISTINCT user_id) FROM strategies;
SELECT 'Users with Trades: ' || COUNT(DISTINCT user_id) FROM trades;

-- Check for duplicate records
SELECT 'Duplicate API Keys: ' || COUNT(*) 
FROM (
    SELECT user_id, exchange, COUNT(*) 
    FROM api_keys 
    GROUP BY user_id, exchange 
    HAVING COUNT(*) > 1
) AS duplicates;

SELECT 'Duplicate Strategies: ' || COUNT(*) 
FROM (
    SELECT user_id, name, COUNT(*) 
    FROM strategies 
    GROUP BY user_id, name 
    HAVING COUNT(*) > 1
) AS duplicates;
"

VERIFICATION_FILE="verification_queries.sql"
echo "$VERIFICATION_SCRIPT" > $VERIFICATION_FILE

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

# Run verification queries
export PGPASSWORD=$DB_PASSWORD
VERIFICATION_RESULT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $VERIFICATION_FILE 2>&1)
if [ $? -ne 0 ]; then
    log "Warning: Data verification queries failed: $VERIFICATION_RESULT"
    log "This may be because some tables don't exist. Please verify the data manually."
else
    log "Data verification completed. Results:"
    echo "$VERIFICATION_RESULT"
fi

# Clean up
rm $VERIFICATION_FILE 2>/dev/null

# Final steps and summary
log "Data migration completed successfully!"
log ""
log "Summary:"
log "- Database data migrated"
log "- Historical market data migrated"
log "- User data, API keys, and settings migrated"
log ""
log "All logs are available in the logs directory:"
log "- Master log: $LOG_FILE"
log ""
log "If you encounter any issues, you can restore from the backup files created during migration."
log "Each migration script created a backup directory with the exported data."
log ""
log "Next steps:"
log "1. Verify that all services are working correctly with the migrated data"
log "2. Update configuration files to point to the local PostgreSQL installation"
log "3. Restart all services to apply the changes"
log ""
log "Thank you for using the Cryptobot Data Migration Tool!"

exit 0