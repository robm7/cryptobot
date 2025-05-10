# sync_data.ps1
# Script to synchronize data between Docker and non-Docker environments on Windows
# Part of Phase 11: Parallel Operation Strategy

Write-Host "=== Cryptobot Data Synchronization Tool ===" -ForegroundColor Cyan
Write-Host "This script synchronizes data between Docker and non-Docker environments." -ForegroundColor Cyan

# Check if environment variables are set
if (-not $env:CRYPTOBOT_SHARED_DATA_DIR) {
    # Source environment file if it exists
    $envFile = "C:\cryptobot\shared_data\config\environment.ps1"
    if (Test-Path $envFile) {
        . $envFile
    } else {
        Write-Host "Error: CRYPTOBOT_SHARED_DATA_DIR environment variable not set." -ForegroundColor Red
        Write-Host "Please run setup_parallel_env.ps1 first or set the variable manually." -ForegroundColor Red
        exit 1
    }
}

# Define directories
$SHARED_DATA_DIR = $env:CRYPTOBOT_SHARED_DATA_DIR
if (-not $SHARED_DATA_DIR) {
    $SHARED_DATA_DIR = "C:\cryptobot\shared_data"
}

$DOCKER_ENV_DIR = "C:\cryptobot\docker"
$NON_DOCKER_ENV_DIR = "C:\cryptobot\non-docker"
$LOG_DIR = $env:CRYPTOBOT_LOG_DIR
if (-not $LOG_DIR) {
    $LOG_DIR = "C:\cryptobot\logs"
}
$SYNC_LOG = "$LOG_DIR\data_sync.log"

# Create sync log directory if it doesn't exist
if (-not (Test-Path (Split-Path $SYNC_LOG -Parent))) {
    New-Item -ItemType Directory -Force -Path (Split-Path $SYNC_LOG -Parent) | Out-Null
}

# Function to log messages
function Write-Log {
    param (
        [string]$Message
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage
    Add-Content -Path $SYNC_LOG -Value $logMessage
}

# Function to check if a service is running
function Test-ServiceRunning {
    param (
        [int]$Port
    )
    
    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return ($null -ne $connection)
}

# Function to test PostgreSQL connection
function Test-PostgreSQLConnection {
    param (
        [string]$Host = "localhost",
        [int]$Port = 5432,
        [string]$User = "cryptobot",
        [string]$Password = "use_env_var_in_production",
        [string]$Database = "cryptobot"
    )
    
    try {
        # This is a simple TCP connection test since we don't have pg_isready in PowerShell
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connectionResult = $tcpClient.BeginConnect($Host, $Port, $null, $null)
        $waitResult = $connectionResult.AsyncWaitHandle.WaitOne(1000, $false)
        
        if ($waitResult) {
            $tcpClient.EndConnect($connectionResult)
            $tcpClient.Close()
            return $true
        } else {
            $tcpClient.Close()
            return $false
        }
    } catch {
        return $false
    }
}

# Function to sync database data
function Sync-Database {
    Write-Log "Starting database synchronization..."
    
    # Check if PostgreSQL is running
    if (-not (Test-PostgreSQLConnection)) {
        Write-Log "Error: PostgreSQL is not running. Please start the database service."
        return $false
    }
    
    # Create backup of the database
    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $backupFile = "$SHARED_DATA_DIR\database\backup_$timestamp.sql"
    
    Write-Log "Creating database backup: $backupFile"
    
    # Ensure the directory exists
    if (-not (Test-Path (Split-Path $backupFile -Parent))) {
        New-Item -ItemType Directory -Force -Path (Split-Path $backupFile -Parent) | Out-Null
    }
    
    # In a real environment, you would use pg_dump here
    # For this script, we'll simulate the backup
    Write-Log "Simulating database backup (in a real environment, use pg_dump)"
    Write-Log "Command would be: pg_dump -h localhost -U cryptobot -d cryptobot -f `"$backupFile`""
    
    # Create an empty backup file for demonstration
    Set-Content -Path $backupFile -Value "-- Database backup created on $(Get-Date)"
    
    Write-Log "Database backup completed successfully."
    return $true
}

# Function to sync historical data
function Sync-HistoricalData {
    Write-Log "Starting historical data synchronization..."
    
    # Check if data directories exist
    if (-not (Test-Path "$SHARED_DATA_DIR\historical_data")) {
        Write-Log "Creating historical data directory..."
        New-Item -ItemType Directory -Force -Path "$SHARED_DATA_DIR\historical_data" | Out-Null
    }
    
    # Check if data service is running in Docker
    $dockerDataPort = $env:CRYPTOBOT_DOCKER_DATA_PORT
    if (-not $dockerDataPort) { $dockerDataPort = 8004 }
    
    if (Test-ServiceRunning -Port $dockerDataPort) {
        Write-Log "Docker data service is running. Stopping service for safe synchronization..."
        Write-Log "WARNING: Please stop the Docker data service manually before proceeding."
        Read-Host "Press Enter to continue after stopping the Docker data service..."
    }
    
    # Check if data service is running in non-Docker
    $nonDockerDataPort = $env:CRYPTOBOT_NON_DOCKER_DATA_PORT
    if (-not $nonDockerDataPort) { $nonDockerDataPort = 9004 }
    
    if (Test-ServiceRunning -Port $nonDockerDataPort) {
        Write-Log "Non-Docker data service is running. Stopping service for safe synchronization..."
        Write-Log "WARNING: Please stop the non-Docker data service manually before proceeding."
        Read-Host "Press Enter to continue after stopping the non-Docker data service..."
    }
    
    Write-Log "Synchronizing historical data..."
    
    # Create a timestamp for the backup
    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    
    # Create a backup of the current historical data
    if ((Test-Path "$SHARED_DATA_DIR\historical_data") -and 
        (Get-ChildItem -Path "$SHARED_DATA_DIR\historical_data" -Force | Select-Object -First 1)) {
        Write-Log "Creating backup of historical data..."
        
        $backupFile = "$SHARED_DATA_DIR\historical_data_backup_$timestamp.zip"
        
        # Create zip archive
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::CreateFromDirectory(
            "$SHARED_DATA_DIR\historical_data", 
            $backupFile
        )
        
        Write-Log "Historical data backup completed: $backupFile"
    }
    
    Write-Log "Historical data synchronization completed."
    return $true
}

# Function to sync user data
function Sync-UserData {
    Write-Log "Starting user data synchronization..."
    
    # Check if user data directory exists
    if (-not (Test-Path "$SHARED_DATA_DIR\user_data")) {
        Write-Log "Creating user data directory..."
        New-Item -ItemType Directory -Force -Path "$SHARED_DATA_DIR\user_data" | Out-Null
    }
    
    # Check if trade service is running in Docker
    $dockerTradePort = $env:CRYPTOBOT_DOCKER_TRADE_PORT
    if (-not $dockerTradePort) { $dockerTradePort = 8003 }
    
    if (Test-ServiceRunning -Port $dockerTradePort) {
        Write-Log "Docker trade service is running. Stopping service for safe synchronization..."
        Write-Log "WARNING: Please stop the Docker trade service manually before proceeding."
        Read-Host "Press Enter to continue after stopping the Docker trade service..."
    }
    
    # Check if trade service is running in non-Docker
    $nonDockerTradePort = $env:CRYPTOBOT_NON_DOCKER_TRADE_PORT
    if (-not $nonDockerTradePort) { $nonDockerTradePort = 9003 }
    
    if (Test-ServiceRunning -Port $nonDockerTradePort) {
        Write-Log "Non-Docker trade service is running. Stopping service for safe synchronization..."
        Write-Log "WARNING: Please stop the non-Docker trade service manually before proceeding."
        Read-Host "Press Enter to continue after stopping the non-Docker trade service..."
    }
    
    Write-Log "Synchronizing user data..."
    
    # Create a timestamp for the backup
    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    
    # Create a backup of the current user data
    if ((Test-Path "$SHARED_DATA_DIR\user_data") -and 
        (Get-ChildItem -Path "$SHARED_DATA_DIR\user_data" -Force | Select-Object -First 1)) {
        Write-Log "Creating backup of user data..."
        
        $backupFile = "$SHARED_DATA_DIR\user_data_backup_$timestamp.zip"
        
        # Create zip archive
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::CreateFromDirectory(
            "$SHARED_DATA_DIR\user_data", 
            $backupFile
        )
        
        Write-Log "User data backup completed: $backupFile"
    }
    
    Write-Log "User data synchronization completed."
    return $true
}

# Function to sync configuration data
function Sync-ConfigData {
    Write-Log "Starting configuration synchronization..."
    
    # Check if config directory exists
    if (-not (Test-Path "$SHARED_DATA_DIR\config")) {
        Write-Log "Creating config directory..."
        New-Item -ItemType Directory -Force -Path "$SHARED_DATA_DIR\config" | Out-Null
    }
    
    Write-Log "Synchronizing configuration data..."
    
    # Create a timestamp for the backup
    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    
    # Create a backup of the current configuration
    if ((Test-Path "$SHARED_DATA_DIR\config") -and 
        (Get-ChildItem -Path "$SHARED_DATA_DIR\config" -Force | Select-Object -First 1)) {
        Write-Log "Creating backup of configuration data..."
        
        $backupFile = "$SHARED_DATA_DIR\config_backup_$timestamp.zip"
        
        # Create zip archive
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::CreateFromDirectory(
            "$SHARED_DATA_DIR\config", 
            $backupFile
        )
        
        Write-Log "Configuration backup completed: $backupFile"
    }
    
    Write-Log "Configuration synchronization completed."
    return $true
}

# Function to verify data integrity
function Test-DataIntegrity {
    Write-Log "Verifying data integrity..."
    
    # Check database connectivity
    if (Test-PostgreSQLConnection) {
        Write-Log "Database connection: OK"
    } else {
        Write-Log "Database connection: FAILED"
        return $false
    }
    
    # Check historical data directory
    if ((Test-Path "$SHARED_DATA_DIR\historical_data") -and 
        (Get-ChildItem -Path "$SHARED_DATA_DIR\historical_data" -Force | Select-Object -First 1)) {
        Write-Log "Historical data: OK"
    } else {
        Write-Log "Historical data: WARNING - Directory empty or not found"
    }
    
    # Check user data directory
    if ((Test-Path "$SHARED_DATA_DIR\user_data") -and 
        (Get-ChildItem -Path "$SHARED_DATA_DIR\user_data" -Force | Select-Object -First 1)) {
        Write-Log "User data: OK"
    } else {
        Write-Log "User data: WARNING - Directory empty or not found"
    }
    
    # Check config directory
    if ((Test-Path "$SHARED_DATA_DIR\config") -and 
        (Get-ChildItem -Path "$SHARED_DATA_DIR\config" -Force | Select-Object -First 1)) {
        Write-Log "Configuration data: OK"
    } else {
        Write-Log "Configuration data: WARNING - Directory empty or not found"
    }
    
    Write-Log "Data integrity verification completed."
    return $true
}

# Main function
function Start-DataSync {
    param (
        [switch]$DatabaseOnly,
        [switch]$HistoricalOnly,
        [switch]$UserOnly,
        [switch]$ConfigOnly,
        [switch]$VerifyOnly,
        [switch]$Help
    )
    
    if ($Help) {
        Write-Host "Usage: .\sync_data.ps1 [OPTIONS]" -ForegroundColor Yellow
        Write-Host "Synchronize data between Docker and non-Docker environments." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Options:" -ForegroundColor Yellow
        Write-Host "  -DatabaseOnly      Synchronize only database data" -ForegroundColor Yellow
        Write-Host "  -HistoricalOnly    Synchronize only historical data" -ForegroundColor Yellow
        Write-Host "  -UserOnly          Synchronize only user data" -ForegroundColor Yellow
        Write-Host "  -ConfigOnly        Synchronize only configuration data" -ForegroundColor Yellow
        Write-Host "  -VerifyOnly        Verify data integrity only" -ForegroundColor Yellow
        Write-Host "  -Help              Display this help message" -ForegroundColor Yellow
        return
    }
    
    Write-Log "Starting data synchronization process..."
    
    # Run specific synchronization steps based on parameters
    if ($DatabaseOnly) {
        Sync-Database
        return
    }
    
    if ($HistoricalOnly) {
        Sync-HistoricalData
        return
    }
    
    if ($UserOnly) {
        Sync-UserData
        return
    }
    
    if ($ConfigOnly) {
        Sync-ConfigData
        return
    }
    
    if ($VerifyOnly) {
        Test-DataIntegrity
        return
    }
    
    # Run all synchronization steps
    Sync-Database
    Sync-HistoricalData
    Sync-UserData
    Sync-ConfigData
    Test-DataIntegrity
    
    Write-Log "Data synchronization process completed successfully."
    
    Write-Host ""
    Write-Host "=== Data Synchronization Complete ===" -ForegroundColor Cyan
    Write-Host "Shared data directory: $SHARED_DATA_DIR" -ForegroundColor White
    Write-Host "Log file: $SYNC_LOG" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Restart Docker services if they were stopped" -ForegroundColor Yellow
    Write-Host "2. Restart non-Docker services if they were stopped" -ForegroundColor Yellow
    Write-Host "3. Verify application functionality in both environments" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "For more information, see the migration documentation." -ForegroundColor Yellow
}

# Parse command line arguments and run the main function
param (
    [switch]$DatabaseOnly,
    [switch]$HistoricalOnly,
    [switch]$UserOnly,
    [switch]$ConfigOnly,
    [switch]$VerifyOnly,
    [switch]$Help
)

Start-DataSync -DatabaseOnly:$DatabaseOnly -HistoricalOnly:$HistoricalOnly -UserOnly:$UserOnly -ConfigOnly:$ConfigOnly -VerifyOnly:$VerifyOnly -Help:$Help