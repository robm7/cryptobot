# Cryptobot Database Migration Script for Windows
# This script migrates database data from Docker volumes to local PostgreSQL

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

Log "Starting database migration from Docker volumes to local PostgreSQL..."

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

# Backup local database before migration
Log "Backing up local database before migration..."
$env:PGPASSWORD = $DB_PASSWORD
$backupFile = "$backupDir\local_db_backup.sql"
$backupResult = & pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -f $backupFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Failed to backup local database: $backupResult"
    Log "Continuing with migration..."
} else {
    Log "Local database backup created: $backupFile"
}

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

# Get Docker volume name
Log "Identifying Docker volume for PostgreSQL data..."
$volumeInfo = docker volume inspect postgres_data 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Error: Could not find Docker volume 'postgres_data'. Please check your Docker setup."
    exit 1
}

# Extract data from Docker container
Log "Extracting database data from Docker container..."
$tempDir = "temp_postgres_data"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

# Create a temporary container to access the volume
Log "Creating temporary container to access volume data..."
$tempContainer = docker run -d --rm -v postgres_data:/var/lib/postgresql/data --name temp_postgres_data alpine:latest tail -f /dev/null
if ($LASTEXITCODE -ne 0) {
    Log "Error: Failed to create temporary container."
    exit 1
}

# Export database from Docker
Log "Exporting database from Docker container..."
$dockerDbBackup = "$backupDir\docker_db_backup.sql"
$exportResult = docker exec cryptobot_postgres pg_dump -U cryptobot -d cryptobot > $dockerDbBackup 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Error: Failed to export database from Docker: $exportResult"
    
    # Try alternative approach with temporary container
    Log "Trying alternative approach..."
    $exportResult = docker exec temp_postgres_data sh -c "pg_dump -U cryptobot -d cryptobot" > $dockerDbBackup 2>&1
    if ($LASTEXITCODE -ne 0) {
        Log "Error: Failed to export database using alternative approach: $exportResult"
        Log "Cleaning up temporary container..."
        docker stop $tempContainer | Out-Null
        exit 1
    }
}

# Clean up temporary container
Log "Cleaning up temporary container..."
docker stop $tempContainer | Out-Null

# Import data to local PostgreSQL
Log "Importing data to local PostgreSQL..."
$env:PGPASSWORD = $DB_PASSWORD
$importResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $dockerDbBackup 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Error: Failed to import database to local PostgreSQL: $importResult"
    Log "Rolling back to previous state..."
    
    # Restore from backup
    $restoreResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $backupFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        Log "Error: Failed to restore database from backup: $restoreResult"
        Log "Database may be in an inconsistent state. Please restore manually from backup: $backupFile"
    } else {
        Log "Database restored from backup."
    }
    
    exit 1
}

# Verify data migration
Log "Verifying data migration..."
$verifyResult = & psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM users;" 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Warning: Verification query failed: $verifyResult"
    Log "Please verify the database manually."
} else {
    Log "Verification successful. User count: $verifyResult"
}

# Clean up
Log "Cleaning up temporary files..."
Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue

Log "Database migration completed successfully!"
Log "Backup files are stored in: $backupDir"
Log "If you encounter any issues, you can restore from the backup using:"
Log "psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $backupFile"

exit 0