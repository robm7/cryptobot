#!/bin/bash
# Cryptobot Data Migration Verification Script for Linux/macOS
# This script verifies the integrity of migrated data

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

log "Starting data migration verification..."

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

# Check if PostgreSQL is installed and running
log "Checking PostgreSQL installation..."
export PGPASSWORD=$DB_PASSWORD
if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
    log "Error: PostgreSQL is not running or not properly configured. Please run setup_database.sh first."
    exit 1
fi

# Create a report directory
REPORT_DIR="migration_report_$(date '+%Y%m%d_%H%M%S')"
mkdir -p $REPORT_DIR
log "Created report directory: $REPORT_DIR"

# Verify database schema
log "Verifying database schema..."
SCHEMA_VERIFICATION_SCRIPT="
-- List all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;

-- List all sequences
SELECT sequence_name 
FROM information_schema.sequences 
WHERE sequence_schema = 'public'
ORDER BY sequence_name;

-- List all indexes
SELECT indexname, tablename 
FROM pg_indexes 
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- List all constraints
SELECT conname, contype, conrelid::regclass AS table_name
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
ORDER BY conrelid::regclass::text, conname;
"

SCHEMA_VERIFICATION_FILE="$REPORT_DIR/schema_verification.sql"
echo "$SCHEMA_VERIFICATION_SCRIPT" > $SCHEMA_VERIFICATION_FILE

SCHEMA_REPORT="$REPORT_DIR/schema_report.txt"
SCHEMA_VERIFICATION_RESULT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $SCHEMA_VERIFICATION_FILE 2>&1)
if [ $? -ne 0 ]; then
    log "Warning: Schema verification queries failed: $SCHEMA_VERIFICATION_RESULT"
    log "This may be because some objects don't exist. Please verify the schema manually."
else
    echo "$SCHEMA_VERIFICATION_RESULT" > $SCHEMA_REPORT
    log "Schema verification completed. Results saved to: $SCHEMA_REPORT"
fi

# Verify data counts
log "Verifying data counts..."
DATA_COUNT_SCRIPT="
-- Count records in each table
SELECT 'users' AS table_name, COUNT(*) AS record_count FROM users
UNION ALL
SELECT 'api_keys', COUNT(*) FROM api_keys
UNION ALL
SELECT 'strategies', COUNT(*) FROM strategies
UNION ALL
SELECT 'trades', COUNT(*) FROM trades
UNION ALL
SELECT 'sessions', COUNT(*) FROM sessions
UNION ALL
SELECT 'ohlcv', COUNT(*) FROM ohlcv
UNION ALL
SELECT 'backtest_results', COUNT(*) FROM backtest_results
UNION ALL
SELECT 'user_settings', COUNT(*) FROM user_settings
UNION ALL
SELECT 'user_preferences', COUNT(*) FROM user_preferences
ORDER BY table_name;
"

DATA_COUNT_FILE="$REPORT_DIR/data_count.sql"
echo "$DATA_COUNT_SCRIPT" > $DATA_COUNT_FILE

DATA_COUNT_REPORT="$REPORT_DIR/data_count_report.txt"
DATA_COUNT_RESULT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $DATA_COUNT_FILE 2>&1)
if [ $? -ne 0 ]; then
    log "Warning: Data count queries failed: $DATA_COUNT_RESULT"
    log "This may be because some tables don't exist. Please verify the data manually."
else
    echo "$DATA_COUNT_RESULT" > $DATA_COUNT_REPORT
    log "Data count verification completed. Results saved to: $DATA_COUNT_REPORT"
fi

# Verify data integrity
log "Verifying data integrity..."
DATA_INTEGRITY_SCRIPT="
-- Check for orphaned records
SELECT 'Orphaned API Keys' AS check_type, COUNT(*) AS count
FROM api_keys ak 
WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = ak.user_id)
UNION ALL
SELECT 'Orphaned Strategies', COUNT(*) 
FROM strategies s 
WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = s.user_id)
UNION ALL
SELECT 'Orphaned Trades', COUNT(*) 
FROM trades t 
WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = t.user_id)
UNION ALL
SELECT 'Orphaned User Settings', COUNT(*) 
FROM user_settings us 
WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = us.user_id)
UNION ALL
SELECT 'Orphaned User Preferences', COUNT(*) 
FROM user_preferences up 
WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = up.user_id);

-- Check for duplicate records
SELECT 'Duplicate API Keys' AS check_type, COUNT(*) AS count
FROM (
    SELECT user_id, exchange, COUNT(*) 
    FROM api_keys 
    GROUP BY user_id, exchange 
    HAVING COUNT(*) > 1
) AS duplicates
UNION ALL
SELECT 'Duplicate Strategies', COUNT(*) 
FROM (
    SELECT user_id, name, COUNT(*) 
    FROM strategies 
    GROUP BY user_id, name 
    HAVING COUNT(*) > 1
) AS duplicates
UNION ALL
SELECT 'Duplicate User Settings', COUNT(*) 
FROM (
    SELECT user_id, setting_key, COUNT(*) 
    FROM user_settings 
    GROUP BY user_id, setting_key 
    HAVING COUNT(*) > 1
) AS duplicates
UNION ALL
SELECT 'Duplicate User Preferences', COUNT(*) 
FROM (
    SELECT user_id, COUNT(*) 
    FROM user_preferences 
    GROUP BY user_id 
    HAVING COUNT(*) > 1
) AS duplicates;

-- Check for invalid data
SELECT 'Invalid Email Addresses' AS check_type, COUNT(*) AS count
FROM users 
WHERE email NOT LIKE '%@%.%'
UNION ALL
SELECT 'Users Without API Keys', COUNT(*) 
FROM users u 
WHERE NOT EXISTS (SELECT 1 FROM api_keys ak WHERE ak.user_id = u.id)
UNION ALL
SELECT 'API Keys With Empty Secrets', COUNT(*) 
FROM api_keys 
WHERE api_secret = '';
"

DATA_INTEGRITY_FILE="$REPORT_DIR/data_integrity.sql"
echo "$DATA_INTEGRITY_SCRIPT" > $DATA_INTEGRITY_FILE

DATA_INTEGRITY_REPORT="$REPORT_DIR/data_integrity_report.txt"
DATA_INTEGRITY_RESULT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $DATA_INTEGRITY_FILE 2>&1)
if [ $? -ne 0 ]; then
    log "Warning: Data integrity queries failed: $DATA_INTEGRITY_RESULT"
    log "This may be because some tables don't exist. Please verify the data manually."
else
    echo "$DATA_INTEGRITY_RESULT" > $DATA_INTEGRITY_REPORT
    log "Data integrity verification completed. Results saved to: $DATA_INTEGRITY_REPORT"
fi

# Verify historical data
log "Verifying historical data..."
HISTORICAL_DATA_SCRIPT="
-- Check OHLCV data distribution
SELECT 
    exchange,
    symbol,
    MIN(time) AS earliest_data,
    MAX(time) AS latest_data,
    COUNT(*) AS record_count
FROM ohlcv
GROUP BY exchange, symbol
ORDER BY exchange, symbol;

-- Check for gaps in OHLCV data (for 1-hour intervals)
WITH time_series AS (
    SELECT 
        exchange,
        symbol,
        date_trunc('hour', time) AS hour,
        COUNT(*) AS records
    FROM ohlcv
    GROUP BY exchange, symbol, date_trunc('hour', time)
),
gaps AS (
    SELECT 
        exchange,
        symbol,
        hour,
        LEAD(hour) OVER (PARTITION BY exchange, symbol ORDER BY hour) AS next_hour,
        LEAD(hour) OVER (PARTITION BY exchange, symbol ORDER BY hour) - hour AS gap
    FROM time_series
)
SELECT 
    exchange,
    symbol,
    hour,
    next_hour,
    gap
FROM gaps
WHERE gap > INTERVAL '1 hour'
LIMIT 100;  -- Limit to 100 gaps to avoid overwhelming output

-- Check backtest results
SELECT 
    user_id,
    strategy_id,
    exchange,
    symbol,
    start_time,
    end_time,
    created_at
FROM backtest_results
ORDER BY created_at DESC
LIMIT 20;  -- Show the 20 most recent backtest results
"

HISTORICAL_DATA_FILE="$REPORT_DIR/historical_data.sql"
echo "$HISTORICAL_DATA_SCRIPT" > $HISTORICAL_DATA_FILE

HISTORICAL_DATA_REPORT="$REPORT_DIR/historical_data_report.txt"
HISTORICAL_DATA_RESULT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $HISTORICAL_DATA_FILE 2>&1)
if [ $? -ne 0 ]; then
    log "Warning: Historical data queries failed: $HISTORICAL_DATA_RESULT"
    log "This may be because the OHLCV table doesn't exist or is empty. Please verify the data manually."
else
    echo "$HISTORICAL_DATA_RESULT" > $HISTORICAL_DATA_REPORT
    log "Historical data verification completed. Results saved to: $HISTORICAL_DATA_REPORT"
fi

# Generate summary report
log "Generating summary report..."
SUMMARY_REPORT="$REPORT_DIR/summary_report.txt"

cat > $SUMMARY_REPORT << EOF
Cryptobot Data Migration Verification Summary
=============================================
Date: $(date '+%Y-%m-%d %H:%M:%S')

Database Connection:
- Host: $DB_HOST
- Port: $DB_PORT
- Database: $DB_NAME
- User: $DB_USER

Verification Results:
- Schema verification: $(if [ -f "$SCHEMA_REPORT" ]; then echo "Completed"; else echo "Failed"; fi)
- Data count verification: $(if [ -f "$DATA_COUNT_REPORT" ]; then echo "Completed"; else echo "Failed"; fi)
- Data integrity verification: $(if [ -f "$DATA_INTEGRITY_REPORT" ]; then echo "Completed"; else echo "Failed"; fi)
- Historical data verification: $(if [ -f "$HISTORICAL_DATA_REPORT" ]; then echo "Completed"; else echo "Failed"; fi)

Please review the detailed reports in the $REPORT_DIR directory.

Next Steps:
1. Review the detailed reports for any issues
2. Fix any data integrity issues found
3. Verify that all services are working correctly with the migrated data
4. Update configuration files to point to the local PostgreSQL installation
5. Restart all services to apply the changes

If you encounter any issues, you can restore from the backup files created during migration.
Each migration script created a backup directory with the exported data.
EOF

log "Summary report generated: $SUMMARY_REPORT"

# Clean up
rm $SCHEMA_VERIFICATION_FILE 2>/dev/null
rm $DATA_COUNT_FILE 2>/dev/null
rm $DATA_INTEGRITY_FILE 2>/dev/null
rm $HISTORICAL_DATA_FILE 2>/dev/null

log "Data migration verification completed successfully!"
log "All reports are available in the $REPORT_DIR directory."
log "Please review the summary report: $SUMMARY_REPORT"

exit 0