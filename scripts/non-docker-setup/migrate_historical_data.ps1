# Cryptobot Historical Data Migration Script for Windows
# This script migrates historical market data from Docker TimescaleDB to local PostgreSQL

# Function to display messages
function Log {
    param (
        [string]$Message
    )
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
}

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Log "Error: This script must be run as Administrator. Please restart PowerShell as Administrator and try again."
    exit 1
}

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Force -Path "logs" | Out-Null
}

Log "Starting historical data migration from Docker TimescaleDB to local PostgreSQL..."

# Load environment variables from .env file if it exists
if (Test-Path .env) {
    Log "Loading environment variables from .env file..."
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^#][^=]*)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Variable -Name $key -Value $value
        }
    }
} else {
    Log "Warning: .env file not found. Using default values."
}

# Set default values if not defined in .env
if (-not (Get-Variable -Name "DB_HOST" -ErrorAction SilentlyContinue)) { $DB_HOST = "localhost" }
if (-not (Get-Variable -Name "DB_PORT" -ErrorAction SilentlyContinue)) { $DB_PORT = "5432" }
if (-not (Get-Variable -Name "DB_USER" -ErrorAction SilentlyContinue)) { $DB_USER = "cryptobot" }
if (-not (Get-Variable -Name "DB_PASSWORD" -ErrorAction SilentlyContinue)) { $DB_PASSWORD = "changeme" }
if (-not (Get-Variable -Name "DB_NAME" -ErrorAction SilentlyContinue)) { $DB_NAME = "cryptobot" }
if (-not (Get-Variable -Name "TIMESCALE_PASSWORD" -ErrorAction SilentlyContinue)) { $TIMESCALE_PASSWORD = "password" }

# Check if Docker is installed and running
Log "Checking Docker installation..."
$dockerCheck = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Error: Docker is not running or not installed. Please start Docker and try again."
    exit 1
}

# Check if PostgreSQL is installed and running
Log "Checking PostgreSQL installation..."
$pgCheck = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1" 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Error: PostgreSQL is not running or not properly configured. Please run setup_database.ps1 first."
    exit 1
}

# Create backup directory
$backupDir = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
Log "Created backup directory: $backupDir"

# Check if TimescaleDB extension is installed in local PostgreSQL
Log "Checking if TimescaleDB extension is installed in local PostgreSQL..."
$env:PGPASSWORD = $DB_PASSWORD
$extensionCheck = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT extname FROM pg_extension WHERE extname = 'timescaledb';" -t 2>&1
if ($extensionCheck -notmatch "timescaledb") {
    Log "TimescaleDB extension not found in local PostgreSQL."
    Log "Attempting to create TimescaleDB extension..."
    
    $createExtResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS timescaledb;" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Log "Error: Failed to create TimescaleDB extension: $createExtResult"
        Log "Please install TimescaleDB extension manually and try again."
        exit 1
    }
    
    Log "TimescaleDB extension created successfully."
}

# Check if the Docker container is running
Log "Checking if Docker containers are running..."
$containerCheck = docker ps -q -f name=timescale 2>&1
if (-not $containerCheck) {
    Log "Warning: Docker container 'timescale' is not running."
    
    # Check if the container exists but is stopped
    $stoppedContainer = docker ps -a -q -f name=timescale 2>&1
    if ($stoppedContainer) {
        Log "Found stopped container. Starting it temporarily for migration..."
        docker start timescale
        Start-Sleep -Seconds 10  # Wait for container to start
    } else {
        Log "Error: Docker container 'timescale' does not exist."
        Log "Attempting to use Docker volume directly..."
    }
}

# Create necessary tables in local PostgreSQL for historical data
Log "Creating necessary tables for historical data in local PostgreSQL..."
$createTablesScript = @"
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
"@

$createTablesFile = "$backupDir\create_tables.sql"
Set-Content -Path $createTablesFile -Value $createTablesScript

$env:PGPASSWORD = $DB_PASSWORD
$createTablesResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $createTablesFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Error: Failed to create tables in local PostgreSQL: $createTablesResult"
    exit 1
}

# Export historical data from Docker TimescaleDB
Log "Exporting historical data from Docker TimescaleDB..."
$ohlcvBackupFile = "$backupDir\ohlcv_data.csv"
$backtestBackupFile = "$backupDir\backtest_results.csv"

# Export OHLCV data
Log "Exporting OHLCV data..."
$exportOhlcvResult = docker exec timescale psql -U postgres -d cryptobot -c "COPY (SELECT * FROM ohlcv) TO STDOUT WITH CSV HEADER" > $ohlcvBackupFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Error: Failed to export OHLCV data from Docker: $exportOhlcvResult"
    Log "Trying alternative approach..."
    
    # Create a temporary container to access the volume
    Log "Creating temporary container to access volume data..."
    $tempContainer = docker run -d --rm -v timescale_data:/var/lib/postgresql/data --name temp_timescale_data alpine:latest tail -f /dev/null
    if ($LASTEXITCODE -ne 0) {
        Log "Error: Failed to create temporary container."
        exit 1
    }
    
    # Try alternative approach
    Log "Export failed. This may be due to the container not running or other issues."
    Log "Please ensure the TimescaleDB container is running and try again."
    
    # Clean up temporary container
    Log "Cleaning up temporary container..."
    docker stop $tempContainer | Out-Null
    
    exit 1
}

# Export backtest results
Log "Exporting backtest results..."
$exportBacktestResult = docker exec timescale psql -U postgres -d cryptobot -c "COPY (SELECT * FROM backtest_results) TO STDOUT WITH CSV HEADER" > $backtestBackupFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Failed to export backtest results from Docker: $exportBacktestResult"
    Log "This may be because the table doesn't exist or is empty. Continuing with migration..."
}

# Import data to local PostgreSQL
Log "Importing historical data to local PostgreSQL..."

# Import OHLCV data
if (Test-Path $ohlcvBackupFile) {
    Log "Importing OHLCV data..."
    $env:PGPASSWORD = $DB_PASSWORD
    $importOhlcvResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "COPY ohlcv FROM STDIN WITH CSV HEADER" < $ohlcvBackupFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        Log "Error: Failed to import OHLCV data to local PostgreSQL: $importOhlcvResult"
        exit 1
    }
    Log "OHLCV data imported successfully."
} else {
    Log "Warning: OHLCV data file not found. Skipping import."
}

# Import backtest results
if (Test-Path $backtestBackupFile) {
    Log "Importing backtest results..."
    $env:PGPASSWORD = $DB_PASSWORD
    $importBacktestResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "COPY backtest_results FROM STDIN WITH CSV HEADER" < $backtestBackupFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        Log "Error: Failed to import backtest results to local PostgreSQL: $importBacktestResult"
        exit 1
    }
    Log "Backtest results imported successfully."
} else {
    Log "Warning: Backtest results file not found. Skipping import."
}

# Verify data migration
Log "Verifying data migration..."
$verifyOhlcvResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM ohlcv;" -t 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: OHLCV verification query failed: $verifyOhlcvResult"
} else {
    Log "OHLCV data verification successful. Record count: $verifyOhlcvResult"
}

$verifyBacktestResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM backtest_results;" -t 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Backtest results verification query failed: $verifyBacktestResult"
} else {
    Log "Backtest results verification successful. Record count: $verifyBacktestResult"
}

Log "Historical data migration completed successfully!"
Log "Backup files are stored in: $backupDir"

exit 0