# Cryptobot Data Migration Verification Script for Windows
# This script verifies the integrity of migrated data

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

Log "Starting data migration verification..."

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

# Check if PostgreSQL is installed and running
Log "Checking PostgreSQL installation..."
$env:PGPASSWORD = $DB_PASSWORD
$pgCheck = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1" 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Error: PostgreSQL is not running or not properly configured. Please run setup_database.ps1 first."
    exit 1
}

# Create a report directory
$reportDir = "migration_report_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
Log "Created report directory: $reportDir"

# Verify database schema
Log "Verifying database schema..."
$schemaVerificationScript = @"
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
"@

$schemaVerificationFile = "$reportDir\schema_verification.sql"
Set-Content -Path $schemaVerificationFile -Value $schemaVerificationScript

$schemaReport = "$reportDir\schema_report.txt"
$schemaVerificationResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $schemaVerificationFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Schema verification queries failed: $schemaVerificationResult"
    Log "This may be because some objects don't exist. Please verify the schema manually."
} else {
    $schemaVerificationResult | Out-File -FilePath $schemaReport
    Log "Schema verification completed. Results saved to: $schemaReport"
}

# Verify data counts
Log "Verifying data counts..."
$dataCountScript = @"
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
"@

$dataCountFile = "$reportDir\data_count.sql"
Set-Content -Path $dataCountFile -Value $dataCountScript

$dataCountReport = "$reportDir\data_count_report.txt"
$dataCountResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $dataCountFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Data count queries failed: $dataCountResult"
    Log "This may be because some tables don't exist. Please verify the data manually."
} else {
    $dataCountResult | Out-File -FilePath $dataCountReport
    Log "Data count verification completed. Results saved to: $dataCountReport"
}

# Verify data integrity
Log "Verifying data integrity..."
$dataIntegrityScript = @"
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
"@

$dataIntegrityFile = "$reportDir\data_integrity.sql"
Set-Content -Path $dataIntegrityFile -Value $dataIntegrityScript

$dataIntegrityReport = "$reportDir\data_integrity_report.txt"
$dataIntegrityResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $dataIntegrityFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Data integrity queries failed: $dataIntegrityResult"
    Log "This may be because some tables don't exist. Please verify the data manually."
} else {
    $dataIntegrityResult | Out-File -FilePath $dataIntegrityReport
    Log "Data integrity verification completed. Results saved to: $dataIntegrityReport"
}

# Verify historical data
Log "Verifying historical data..."
$historicalDataScript = @"
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
"@

$historicalDataFile = "$reportDir\historical_data.sql"
Set-Content -Path $historicalDataFile -Value $historicalDataScript

$historicalDataReport = "$reportDir\historical_data_report.txt"
$historicalDataResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $historicalDataFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Historical data queries failed: $historicalDataResult"
    Log "This may be because the OHLCV table doesn't exist or is empty. Please verify the data manually."
} else {
    $historicalDataResult | Out-File -FilePath $historicalDataReport
    Log "Historical data verification completed. Results saved to: $historicalDataReport"
}

# Generate summary report
Log "Generating summary report..."
$summaryReport = "$reportDir\summary_report.txt"

$summary = @"
Cryptobot Data Migration Verification Summary
=============================================
Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

Database Connection:
- Host: $DB_HOST
- Port: $DB_PORT
- Database: $DB_NAME
- User: $DB_USER

Verification Results:
- Schema verification: $(if (Test-Path $schemaReport) { "Completed" } else { "Failed" })
- Data count verification: $(if (Test-Path $dataCountReport) { "Completed" } else { "Failed" })
- Data integrity verification: $(if (Test-Path $dataIntegrityReport) { "Completed" } else { "Failed" })
- Historical data verification: $(if (Test-Path $historicalDataReport) { "Completed" } else { "Failed" })

Please review the detailed reports in the $reportDir directory.

Next Steps:
1. Review the detailed reports for any issues
2. Fix any data integrity issues found
3. Verify that all services are working correctly with the migrated data
4. Update configuration files to point to the local PostgreSQL installation
5. Restart all services to apply the changes

If you encounter any issues, you can restore from the backup files created during migration.
Each migration script created a backup directory with the exported data.
"@

Set-Content -Path $summaryReport -Value $summary
Log "Summary report generated: $summaryReport"

# Clean up
Remove-Item $schemaVerificationFile -ErrorAction SilentlyContinue
Remove-Item $dataCountFile -ErrorAction SilentlyContinue
Remove-Item $dataIntegrityFile -ErrorAction SilentlyContinue
Remove-Item $historicalDataFile -ErrorAction SilentlyContinue

Log "Data migration verification completed successfully!"
Log "All reports are available in the $reportDir directory."
Log "Please review the summary report: $summaryReport"

exit 0