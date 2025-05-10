#!/bin/bash
# Cryptobot Historical Data Migration Script for Linux/macOS
# This script migrates historical market data from Docker TimescaleDB to local PostgreSQL

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

log "Starting historical data migration from Docker TimescaleDB to local PostgreSQL..."

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
TIMESCALE_PASSWORD=${TIMESCALE_PASSWORD:-password}

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

# Check if TimescaleDB extension is installed in local PostgreSQL
log "Checking if TimescaleDB extension is installed in local PostgreSQL..."
export PGPASSWORD=$DB_PASSWORD
EXTENSION_CHECK=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT extname FROM pg_extension WHERE extname = 'timescaledb';" -t 2>/dev/null)
if [[ ! "$EXTENSION_CHECK" =~ "timescaledb" ]]; then
    log "TimescaleDB extension not found in local PostgreSQL."
    log "Attempting to create TimescaleDB extension..."
    
    if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS timescaledb;" > /dev/null 2>&1; then
        log "Error: Failed to create TimescaleDB extension."
        log "Please install TimescaleDB extension manually and try again."
        exit 1
    fi
    
    log "TimescaleDB extension created successfully."
fi

# Check if the Docker container is running
log "Checking if Docker containers are running..."
if ! docker ps -q -f name=timescale > /dev/null 2>&1; then
    log "Warning: Docker container 'timescale' is not running."
    
    # Check if the container exists but is stopped
    if docker ps -a -q -f name=timescale > /dev/null 2>&1; then
        log "Found stopped container. Starting it temporarily for migration..."
        docker start timescale
        sleep 10  # Wait for container to start
    else
        log "Error: Docker container 'timescale' does not exist."
        log "Attempting to use Docker volume directly..."
    fi
fi

# Create necessary tables in local PostgreSQL for historical data
log "Creating necessary tables for historical data in local PostgreSQL..."
CREATE_TABLES_SCRIPT="
-- Create OHLCV table if it doesn't exist
CREATE TABLE IF NOT EXISTS ohlcv (
    time TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DECIMAL(18, 8) NOT NULL,
    high DECIMAL(18, 8) NOT NULL,
    low DECIMAL(18, 8) NOT NULL,
    close DECIMAL(18, 8) NOT NULL,
    volume DECIMAL(18, 8) NOT NULL
);

-- Convert to hypertable if not already
SELECT create_hypertable('ohlcv', 'time', if_not_exists => TRUE);

-- Create index on exchange and symbol
CREATE INDEX IF NOT EXISTS idx_ohlcv_exchange_symbol ON ohlcv (exchange, symbol);

-- Create backtest_results table if it doesn't exist
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    strategy_id INTEGER NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    parameters JSONB NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"

CREATE_TABLES_FILE="$BACKUP_DIR/create_tables.sql"
echo "$CREATE_TABLES_SCRIPT" > $CREATE_TABLES_FILE

export PGPASSWORD=$DB_PASSWORD
if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $CREATE_TABLES_FILE > /dev/null 2>&1; then
    log "Error: Failed to create tables in local PostgreSQL."
    exit 1
fi

# Export historical data from Docker TimescaleDB
log "Exporting historical data from Docker TimescaleDB..."
OHLCV_BACKUP_FILE="$BACKUP_DIR/ohlcv_data.csv"
BACKTEST_BACKUP_FILE="$BACKUP_DIR/backtest_results.csv"

# Export OHLCV data
log "Exporting OHLCV data..."
if ! docker exec timescale psql -U postgres -d cryptobot -c "COPY (SELECT * FROM ohlcv) TO STDOUT WITH CSV HEADER" > $OHLCV_BACKUP_FILE 2>/dev/null; then
    log "Error: Failed to export OHLCV data from Docker."
    log "Trying alternative approach..."
    
    # Create a temporary container to access the volume
    log "Creating temporary container to access volume data..."
    TEMP_CONTAINER=$(docker run -d --rm -v timescale_data:/var/lib/postgresql/data --name temp_timescale_data alpine:latest tail -f /dev/null)
    if [ $? -ne 0 ]; then
        log "Error: Failed to create temporary container."
        exit 1
    fi
    
    # Try alternative approach
    log "Export failed. This may be due to the container not running or other issues."
    log "Please ensure the TimescaleDB container is running and try again."
    
    # Clean up temporary container
    log "Cleaning up temporary container..."
    docker stop $TEMP_CONTAINER > /dev/null 2>&1
    
    exit 1
fi

# Export backtest results
log "Exporting backtest results..."
if ! docker exec timescale psql -U postgres -d cryptobot -c "COPY (SELECT * FROM backtest_results) TO STDOUT WITH CSV HEADER" > $BACKTEST_BACKUP_FILE 2>/dev/null; then
    log "Warning: Failed to export backtest results from Docker."
    log "This may be because the table doesn't exist or is empty. Continuing with migration..."
fi

# Import data to local PostgreSQL
log "Importing historical data to local PostgreSQL..."

# Import OHLCV data
if [ -f $OHLCV_BACKUP_FILE ]; then
    log "Importing OHLCV data..."
    export PGPASSWORD=$DB_PASSWORD
    if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "COPY ohlcv FROM STDIN WITH CSV HEADER" < $OHLCV_BACKUP_FILE > /dev/null 2>&1; then
        log "Error: Failed to import OHLCV data to local PostgreSQL."
        exit 1
    fi
    log "OHLCV data imported successfully."
else
    log "Warning: OHLCV data file not found. Skipping import."
fi

# Import backtest results
if [ -f $BACKTEST_BACKUP_FILE ]; then
    log "Importing backtest results..."
    export PGPASSWORD=$DB_PASSWORD
    if ! psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "COPY backtest_results FROM STDIN WITH CSV HEADER" < $BACKTEST_BACKUP_FILE > /dev/null 2>&1; then
        log "Error: Failed to import backtest results to local PostgreSQL."
        exit 1
    fi
    log "Backtest results imported successfully."
else
    log "Warning: Backtest results file not found. Skipping import."
fi

# Verify data migration
log "Verifying data migration..."
VERIFY_OHLCV_RESULT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM ohlcv;" -t 2>/dev/null)
if [ $? -ne 0 ]; then
    log "Warning: OHLCV verification query failed."
else
    log "OHLCV data verification successful. Record count: $VERIFY_OHLCV_RESULT"
fi

VERIFY_BACKTEST_RESULT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM backtest_results;" -t 2>/dev/null)
if [ $? -ne 0 ]; then
    log "Warning: Backtest results verification query failed."
else
    log "Backtest results verification successful. Record count: $VERIFY_BACKTEST_RESULT"
fi

log "Historical data migration completed successfully!"
log "Backup files are stored in: $BACKUP_DIR"

exit 0