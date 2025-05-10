# Cryptobot User Data Migration Script for Windows
# This script migrates user data, including API keys, preferences, and settings

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

Log "Starting user data migration from Docker to local PostgreSQL..."

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

# Check if the Docker container is running
Log "Checking if Docker containers are running..."
$containerCheck = docker ps -q -f name=cryptobot_postgres 2>&1
if (-not $containerCheck) {
    Log "Warning: Docker container 'cryptobot_postgres' is not running."
    
    # Check if the container exists but is stopped
    $stoppedContainer = docker ps -a -q -f name=cryptobot_postgres 2>&1
    if ($stoppedContainer) {
        Log "Found stopped container. Starting it temporarily for migration..."
        docker start cryptobot_postgres
        Start-Sleep -Seconds 10  # Wait for container to start
    } else {
        Log "Error: Docker container 'cryptobot_postgres' does not exist."
        Log "Attempting to use Docker volume directly..."
    }
}

# Create necessary tables in local PostgreSQL for user data if they don't exist
Log "Ensuring necessary tables exist for user data in local PostgreSQL..."
$createTablesScript = @"
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
"@

$createTablesFile = "$backupDir\create_user_tables.sql"
Set-Content -Path $createTablesFile -Value $createTablesScript

$env:PGPASSWORD = $DB_PASSWORD
$createTablesResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $createTablesFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Error: Failed to create tables in local PostgreSQL: $createTablesResult"
    exit 1
}

# Export user data from Docker PostgreSQL
Log "Exporting user data from Docker PostgreSQL..."
$usersBackupFile = "$backupDir\users_data.csv"
$apiKeysBackupFile = "$backupDir\api_keys_data.csv"
$userSettingsBackupFile = "$backupDir\user_settings_data.csv"
$userPreferencesBackupFile = "$backupDir\user_preferences_data.csv"

# Export users data
Log "Exporting users data..."
$exportUsersResult = docker exec cryptobot_postgres psql -U cryptobot -d cryptobot -c "COPY (SELECT * FROM users) TO STDOUT WITH CSV HEADER" > $usersBackupFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Error: Failed to export users data from Docker: $exportUsersResult"
    Log "This may be because the table doesn't exist or the container is not running."
    Log "Trying alternative approach..."
    
    # Create a temporary container to access the volume
    Log "Creating temporary container to access volume data..."
    $tempContainer = docker run -d --rm -v postgres_data:/var/lib/postgresql/data --name temp_postgres_data alpine:latest tail -f /dev/null
    if ($LASTEXITCODE -ne 0) {
        Log "Error: Failed to create temporary container."
        exit 1
    }
    
    # Try alternative approach
    Log "Export failed. This may be due to the container not running or other issues."
    Log "Please ensure the PostgreSQL container is running and try again."
    
    # Clean up temporary container
    Log "Cleaning up temporary container..."
    docker stop $tempContainer | Out-Null
    
    exit 1
}

# Export API keys data
Log "Exporting API keys data..."
$exportApiKeysResult = docker exec cryptobot_postgres psql -U cryptobot -d cryptobot -c "COPY (SELECT * FROM api_keys) TO STDOUT WITH CSV HEADER" > $apiKeysBackupFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Failed to export API keys data from Docker: $exportApiKeysResult"
    Log "This may be because the table doesn't exist or is empty. Continuing with migration..."
}

# Export user settings data
Log "Exporting user settings data..."
$exportSettingsResult = docker exec cryptobot_postgres psql -U cryptobot -d cryptobot -c "COPY (SELECT * FROM user_settings) TO STDOUT WITH CSV HEADER" > $userSettingsBackupFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Failed to export user settings data from Docker: $exportSettingsResult"
    Log "This may be because the table doesn't exist or is empty. Continuing with migration..."
}

# Export user preferences data
Log "Exporting user preferences data..."
$exportPreferencesResult = docker exec cryptobot_postgres psql -U cryptobot -d cryptobot -c "COPY (SELECT * FROM user_preferences) TO STDOUT WITH CSV HEADER" > $userPreferencesBackupFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Failed to export user preferences data from Docker: $exportPreferencesResult"
    Log "This may be because the table doesn't exist or is empty. Continuing with migration..."
}

# Import data to local PostgreSQL
Log "Importing user data to local PostgreSQL..."

# Import users data
if (Test-Path $usersBackupFile) {
    Log "Importing users data..."
    $env:PGPASSWORD = $DB_PASSWORD
    $importUsersResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "COPY users FROM STDIN WITH CSV HEADER" < $usersBackupFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        Log "Error: Failed to import users data to local PostgreSQL: $importUsersResult"
        exit 1
    }
    Log "Users data imported successfully."
} else {
    Log "Warning: Users data file not found. Skipping import."
}

# Import API keys data
if (Test-Path $apiKeysBackupFile) {
    Log "Importing API keys data..."
    $env:PGPASSWORD = $DB_PASSWORD
    $importApiKeysResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "COPY api_keys FROM STDIN WITH CSV HEADER" < $apiKeysBackupFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        Log "Error: Failed to import API keys data to local PostgreSQL: $importApiKeysResult"
        exit 1
    }
    Log "API keys data imported successfully."
} else {
    Log "Warning: API keys data file not found. Skipping import."
}

# Import user settings data
if (Test-Path $userSettingsBackupFile) {
    Log "Importing user settings data..."
    $env:PGPASSWORD = $DB_PASSWORD
    $importSettingsResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "COPY user_settings FROM STDIN WITH CSV HEADER" < $userSettingsBackupFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        Log "Error: Failed to import user settings data to local PostgreSQL: $importSettingsResult"
        exit 1
    }
    Log "User settings data imported successfully."
} else {
    Log "Warning: User settings data file not found. Skipping import."
}

# Import user preferences data
if (Test-Path $userPreferencesBackupFile) {
    Log "Importing user preferences data..."
    $env:PGPASSWORD = $DB_PASSWORD
    $importPreferencesResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "COPY user_preferences FROM STDIN WITH CSV HEADER" < $userPreferencesBackupFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        Log "Error: Failed to import user preferences data to local PostgreSQL: $importPreferencesResult"
        exit 1
    }
    Log "User preferences data imported successfully."
} else {
    Log "Warning: User preferences data file not found. Skipping import."
}

# Verify data migration
Log "Verifying data migration..."
$verifyUsersResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM users;" -t 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Users verification query failed: $verifyUsersResult"
} else {
    Log "Users data verification successful. Record count: $verifyUsersResult"
}

$verifyApiKeysResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM api_keys;" -t 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: API keys verification query failed: $verifyApiKeysResult"
} else {
    Log "API keys data verification successful. Record count: $verifyApiKeysResult"
}

# Reset sequence values to avoid conflicts
Log "Resetting sequence values..."
$resetSequencesScript = @"
-- Reset users sequence
SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 0) FROM users), true);

-- Reset api_keys sequence
SELECT setval('api_keys_id_seq', (SELECT COALESCE(MAX(id), 0) FROM api_keys), true);

-- Reset user_settings sequence
SELECT setval('user_settings_id_seq', (SELECT COALESCE(MAX(id), 0) FROM user_settings), true);

-- Reset user_preferences sequence
SELECT setval('user_preferences_id_seq', (SELECT COALESCE(MAX(id), 0) FROM user_preferences), true);
"@

$resetSequencesFile = "$backupDir\reset_sequences.sql"
Set-Content -Path $resetSequencesFile -Value $resetSequencesScript

$env:PGPASSWORD = $DB_PASSWORD
$resetSequencesResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $resetSequencesFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Failed to reset sequence values: $resetSequencesResult"
    Log "This may cause issues with new record insertions. Please check manually."
} else {
    Log "Sequence values reset successfully."
}

Log "User data migration completed successfully!"
Log "Backup files are stored in: $backupDir"

exit 0