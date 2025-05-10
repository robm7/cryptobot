# Cryptobot Master Data Migration Script for Windows
# This script orchestrates the execution of all data migration scripts

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

# Display welcome message
Log "Welcome to the Cryptobot Data Migration Tool!"
Log "This script will migrate all data from Docker volumes to the local PostgreSQL installation."
Log "The migration process includes:"
Log "1. Database migration (users, strategies, trades, etc.)"
Log "2. Historical market data migration"
Log "3. User data migration (API keys, preferences, settings)"
Log ""
Log "The migration process may take several minutes to complete, depending on the amount of data."
Log "Please ensure that Docker is running and the PostgreSQL service is installed and running."
Log ""

Write-Host "Press Enter to continue or Ctrl+C to cancel..." -NoNewline
$null = Read-Host

# Create a master log file
$logFile = "logs\data_migration_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
Start-Transcript -Path $logFile -Append

# Step 1: Database Migration
Log "Step 1: Database Migration"
Log "Running migrate_database.ps1..."
$dbOutput = & "$PSScriptRoot\migrate_database.ps1" 2>&1
$dbOutput | Out-File -FilePath "logs\migrate_database.log"
$dbOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Database migration failed. Please check logs\migrate_database.log for details."
    Stop-Transcript
    exit 1
}

Log "Database migration completed successfully!"

# Step 2: Historical Data Migration
Log "Step 2: Historical Data Migration"
Log "Running migrate_historical_data.ps1..."
$histOutput = & "$PSScriptRoot\migrate_historical_data.ps1" 2>&1
$histOutput | Out-File -FilePath "logs\migrate_historical_data.log"
$histOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Historical data migration failed. Please check logs\migrate_historical_data.log for details."
    Stop-Transcript
    exit 1
}

Log "Historical data migration completed successfully!"

# Step 3: User Data Migration
Log "Step 3: User Data Migration"
Log "Running migrate_user_data.ps1..."
$userOutput = & "$PSScriptRoot\migrate_user_data.ps1" 2>&1
$userOutput | Out-File -FilePath "logs\migrate_user_data.log"
$userOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: User data migration failed. Please check logs\migrate_user_data.log for details."
    Stop-Transcript
    exit 1
}

Log "User data migration completed successfully!"

# Step 4: Verify Data Integrity
Log "Step 4: Verifying Data Integrity"
Log "Running data verification checks..."

# Create verification script
$verificationScript = @"
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
"@

$verificationFile = "verification_queries.sql"
Set-Content -Path $verificationFile -Value $verificationScript

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

# Run verification queries
$env:PGPASSWORD = $DB_PASSWORD
$verificationResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $verificationFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Data verification queries failed: $verificationResult"
    Log "This may be because some tables don't exist. Please verify the data manually."
} else {
    Log "Data verification completed. Results:"
    $verificationResult | Write-Host
}

# Clean up
Remove-Item $verificationFile -ErrorAction SilentlyContinue

# Final steps and summary
Log "Data migration completed successfully!"
Log ""
Log "Summary:"
Log "- Database data migrated"
Log "- Historical market data migrated"
Log "- User data, API keys, and settings migrated"
Log ""
Log "All logs are available in the logs directory:"
Log "- Master log: $logFile"
Log "- Database migration log: logs\migrate_database.log"
Log "- Historical data migration log: logs\migrate_historical_data.log"
Log "- User data migration log: logs\migrate_user_data.log"
Log ""
Log "If you encounter any issues, you can restore from the backup files created during migration."
Log "Each migration script created a backup directory with the exported data."
Log ""
Log "Next steps:"
Log "1. Verify that all services are working correctly with the migrated data"
Log "2. Update configuration files to point to the local PostgreSQL installation"
Log "3. Restart all services to apply the changes"
Log ""
Log "Thank you for using the Cryptobot Data Migration Tool!"

Stop-Transcript
exit 0