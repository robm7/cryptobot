<#
.SYNOPSIS
    Restore script for Cryptobot non-Docker installation.
.DESCRIPTION
    This script restores a backup of the Cryptobot application, including configuration, database, and logs.
    It can be used to recover from failures or to roll back changes.
.PARAMETER BackupName
    The name of the backup to restore. Required.
.PARAMETER RestoreLogs
    Whether to restore logs from the backup. Default is false.
.PARAMETER BackupDir
    The directory where backups are stored. Default is "backups" in the root directory.
.NOTES
    File Name      : restore.ps1
    Prerequisite   : PowerShell 5.1 or later
.EXAMPLE
    .\restore.ps1 -BackupName "backup_20250510_120000"
    Restores the backup named "backup_20250510_120000".
.EXAMPLE
    .\restore.ps1 -BackupName "pre_upgrade" -RestoreLogs
    Restores the backup named "pre_upgrade" including logs.
#>

param (
    [Parameter(Mandatory=$true)]
    [string]$BackupName,
    
    [switch]$RestoreLogs = $false,
    
    [string]$BackupDir
)

# Stop on any error
$ErrorActionPreference = "Stop"

# Script variables
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootPath = (Get-Item $ScriptPath).Parent.Parent.FullName
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path -Path $RootPath -ChildPath "logs"
$LogFile = Join-Path -Path $LogPath -ChildPath "restore_$Timestamp.log"

# Create log directory if it doesn't exist
if (-not (Test-Path -Path $LogPath)) {
    New-Item -Path $LogPath -ItemType Directory -Force | Out-Null
}

# Set backup directory
if (-not $BackupDir) {
    $BackupDir = Join-Path -Path $RootPath -ChildPath "backups"
}

# Function to log messages
function Write-Log {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("INFO", "WARNING", "ERROR")]
        [string]$Level = "INFO"
    )
    
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    
    # Write to console
    switch ($Level) {
        "INFO" { Write-Host $LogMessage -ForegroundColor Green }
        "WARNING" { Write-Host $LogMessage -ForegroundColor Yellow }
        "ERROR" { Write-Host $LogMessage -ForegroundColor Red }
    }
    
    # Write to log file
    Add-Content -Path $LogFile -Value $LogMessage
}

# Function to check if a command exists
function Test-CommandExists {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Command
    )
    
    $Exists = $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
    return $Exists
}

# Function to stop services
function Stop-CryptobotServices {
    Write-Log "Stopping Cryptobot services"
    
    $Services = @(
        "CryptobotAuth",
        "CryptobotStrategy",
        "CryptobotBacktest",
        "CryptobotTrade",
        "CryptobotData"
    )
    
    foreach ($Service in $Services) {
        $ServiceObj = Get-Service -Name $Service -ErrorAction SilentlyContinue
        if ($ServiceObj) {
            Write-Log "Stopping service: $Service"
            Stop-Service -Name $Service -Force
        } else {
            Write-Log "Service not found: $Service" -Level "WARNING"
        }
    }
}

# Function to start services
function Start-CryptobotServices {
    Write-Log "Starting Cryptobot services"
    
    $Services = @(
        "CryptobotAuth",
        "CryptobotStrategy",
        "CryptobotBacktest",
        "CryptobotTrade",
        "CryptobotData"
    )
    
    foreach ($Service in $Services) {
        $ServiceObj = Get-Service -Name $Service -ErrorAction SilentlyContinue
        if ($ServiceObj) {
            Write-Log "Starting service: $Service"
            Start-Service -Name $Service
        } else {
            Write-Log "Service not found: $Service" -Level "WARNING"
        }
    }
}

# Main restore process
try {
    Write-Log "Starting restore process: $BackupName"
    
    # Check if backup archive exists
    $BackupArchive = Join-Path -Path $BackupDir -ChildPath "$BackupName.zip"
    if (-not (Test-Path -Path $BackupArchive)) {
        Write-Log "Backup archive not found: $BackupArchive" -Level "ERROR"
        exit 1
    }
    
    # Create temporary directory for extraction
    $TempDir = Join-Path -Path $env:TEMP -ChildPath "cryptobot_restore_$Timestamp"
    if (Test-Path -Path $TempDir) {
        Remove-Item -Path $TempDir -Recurse -Force
    }
    
    New-Item -Path $TempDir -ItemType Directory -Force | Out-Null
    Write-Log "Created temporary directory: $TempDir"
    
    # Extract backup archive
    Write-Log "Extracting backup archive"
    Expand-Archive -Path $BackupArchive -DestinationPath $TempDir
    
    # Check if metadata file exists
    $MetadataFile = Join-Path -Path $TempDir -ChildPath "metadata.json"
    if (-not (Test-Path -Path $MetadataFile)) {
        Write-Log "Metadata file not found in backup: $MetadataFile" -Level "ERROR"
        Remove-Item -Path $TempDir -Recurse -Force
        exit 1
    }
    
    # Read metadata
    $Metadata = Get-Content -Path $MetadataFile -Raw | ConvertFrom-Json
    Write-Log "Backup metadata: Timestamp=$($Metadata.Timestamp), Version=$($Metadata.Version)"
    
    # Stop services before restore
    Stop-CryptobotServices
    
    try {
        # Create backup of current state before restore
        Write-Log "Creating backup of current state before restore"
        $PreRestoreBackupName = "pre_restore_$Timestamp"
        $BackupScript = Join-Path -Path $ScriptPath -ChildPath "backup.ps1"
        & $BackupScript -BackupName $PreRestoreBackupName
        
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Pre-restore backup failed with exit code: $LASTEXITCODE" -Level "WARNING"
            $Confirm = Read-Host "Pre-restore backup failed. Do you want to continue with the restore? (Y/N)"
            if ($Confirm -ne "Y") {
                Write-Log "Restore aborted by user" -Level "WARNING"
                exit 0
            }
        } else {
            Write-Log "Pre-restore backup created: $PreRestoreBackupName"
        }
        
        # 1. Restore configuration
        Write-Log "Restoring configuration"
        $ConfigBackupDir = Join-Path -Path $TempDir -ChildPath "config"
        $ConfigDir = Join-Path -Path $RootPath -ChildPath "config"
        
        if (Test-Path -Path $ConfigBackupDir) {
            # Backup current config
            $ConfigBackup = Join-Path -Path $env:TEMP -ChildPath "cryptobot_config_backup_$Timestamp"
            if (Test-Path -Path $ConfigDir) {
                Copy-Item -Path $ConfigDir -Destination $ConfigBackup -Recurse -Force
                Write-Log "Current configuration backed up to: $ConfigBackup"
                
                # Clear current config
                Remove-Item -Path "$ConfigDir\*" -Recurse -Force
            } else {
                New-Item -Path $ConfigDir -ItemType Directory -Force | Out-Null
            }
            
            # Restore config from backup
            Copy-Item -Path "$ConfigBackupDir\*" -Destination $ConfigDir -Recurse -Force
            Write-Log "Configuration restored from backup"
        } else {
            Write-Log "Configuration not found in backup" -Level "WARNING"
        }
        
        # 2. Restore database
        Write-Log "Restoring database"
        $DbBackupDir = Join-Path -Path $TempDir -ChildPath "database"
        
        if (Test-Path -Path $DbBackupDir) {
            # Check if PostgreSQL is installed
            $PgRestoreExists = Test-CommandExists -Command "pg_restore"
            if ($PgRestoreExists) {
                Write-Log "PostgreSQL detected, using pg_restore"
                
                # Get database connection info from environment or config
                $DbHost = $env:CRYPTOBOT_DB_HOST
                if (-not $DbHost) { $DbHost = "localhost" }
                
                $DbPort = $env:CRYPTOBOT_DB_PORT
                if (-not $DbPort) { $DbPort = "5432" }
                
                $DbUser = $env:CRYPTOBOT_DB_USER
                if (-not $DbUser) { $DbUser = "postgres" }
                
                $DbPassword = $env:CRYPTOBOT_DB_PASSWORD
                if (-not $DbPassword) {
                    Write-Log "Database password not found in environment variables" -Level "WARNING"
                    $DbPassword = Read-Host "Enter database password" -AsSecureString
                    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($DbPassword)
                    $DbPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
                }
                
                $DbName = $env:CRYPTOBOT_DB_NAME
                if (-not $DbName) { $DbName = "cryptobot" }
                
                # Set PGPASSWORD environment variable for pg_restore
                $env:PGPASSWORD = $DbPassword
                
                # Find database dump file
                $DbDumpFile = Join-Path -Path $DbBackupDir -ChildPath "$DbName.sql"
                if (Test-Path -Path $DbDumpFile) {
                    # Drop and recreate database
                    Write-Log "Dropping and recreating database: $DbName"
                    
                    # Use psql to drop and recreate database
                    & psql -h $DbHost -p $DbPort -U $DbUser -c "DROP DATABASE IF EXISTS $DbName;"
                    & psql -h $DbHost -p $DbPort -U $DbUser -c "CREATE DATABASE $DbName;"
                    
                    if ($LASTEXITCODE -eq 0) {
                        # Restore database
                        Write-Log "Restoring database from backup"
                        & pg_restore -h $DbHost -p $DbPort -U $DbUser -d $DbName -v $DbDumpFile
                        
                        if ($LASTEXITCODE -eq 0) {
                            Write-Log "Database restored successfully"
                        } else {
                            Write-Log "Database restore failed with exit code: $LASTEXITCODE" -Level "ERROR"
                        }
                    } else {
                        Write-Log "Failed to recreate database with exit code: $LASTEXITCODE" -Level "ERROR"
                    }
                    
                    # Clear PGPASSWORD environment variable
                    Remove-Item Env:\PGPASSWORD
                } else {
                    Write-Log "Database dump file not found in backup: $DbDumpFile" -Level "WARNING"
                }
            } else {
                # Check if SQLite is used
                $SqliteDbBackup = Join-Path -Path $DbBackupDir -ChildPath "cryptobot.db"
                if (Test-Path -Path $SqliteDbBackup) {
                    Write-Log "SQLite database detected, restoring file"
                    
                    $SqliteDbDir = Join-Path -Path $RootPath -ChildPath "database"
                    if (-not (Test-Path -Path $SqliteDbDir)) {
                        New-Item -Path $SqliteDbDir -ItemType Directory -Force | Out-Null
                    }
                    
                    $SqliteDbPath = Join-Path -Path $SqliteDbDir -ChildPath "cryptobot.db"
                    
                    # Backup current database
                    if (Test-Path -Path $SqliteDbPath) {
                        $SqliteDbBackupPath = Join-Path -Path $env:TEMP -ChildPath "cryptobot_db_backup_$Timestamp.db"
                        Copy-Item -Path $SqliteDbPath -Destination $SqliteDbBackupPath -Force
                        Write-Log "Current SQLite database backed up to: $SqliteDbBackupPath"
                    }
                    
                    # Restore database from backup
                    Copy-Item -Path $SqliteDbBackup -Destination $SqliteDbPath -Force
                    Write-Log "SQLite database restored from backup"
                } else {
                    Write-Log "No database found in backup" -Level "WARNING"
                }
            }
        } else {
            Write-Log "Database not found in backup" -Level "WARNING"
        }
        
        # 3. Restore historical data
        Write-Log "Restoring historical data"
        $DataBackupDir = Join-Path -Path $TempDir -ChildPath "data"
        $DataDir = Join-Path -Path $RootPath -ChildPath "data"
        
        if (Test-Path -Path $DataBackupDir) {
            # Backup current data
            $DataBackup = Join-Path -Path $env:TEMP -ChildPath "cryptobot_data_backup_$Timestamp"
            if (Test-Path -Path $DataDir) {
                Copy-Item -Path $DataDir -Destination $DataBackup -Recurse -Force
                Write-Log "Current historical data backed up to: $DataBackup"
                
                # Clear current data
                Remove-Item -Path "$DataDir\*" -Recurse -Force
            } else {
                New-Item -Path $DataDir -ItemType Directory -Force | Out-Null
            }
            
            # Restore data from backup
            Copy-Item -Path "$DataBackupDir\*" -Destination $DataDir -Recurse -Force
            Write-Log "Historical data restored from backup"
        } else {
            Write-Log "Historical data not found in backup" -Level "WARNING"
        }
        
        # 4. Restore logs (optional)
        if ($RestoreLogs) {
            Write-Log "Restoring logs"
            $LogsBackupDir = Join-Path -Path $TempDir -ChildPath "logs"
            
            if (Test-Path -Path $LogsBackupDir) {
                # Backup current logs
                $LogsBackup = Join-Path -Path $env:TEMP -ChildPath "cryptobot_logs_backup_$Timestamp"
                if (Test-Path -Path $LogPath) {
                    Copy-Item -Path $LogPath -Destination $LogsBackup -Recurse -Force
                    Write-Log "Current logs backed up to: $LogsBackup"
                    
                    # Clear current logs
                    Remove-Item -Path "$LogPath\*" -Recurse -Force
                } else {
                    New-Item -Path $LogPath -ItemType Directory -Force | Out-Null
                }
                
                # Restore logs from backup
                Copy-Item -Path "$LogsBackupDir\*" -Destination $LogPath -Recurse -Force
                Write-Log "Logs restored from backup"
            } else {
                Write-Log "Logs not found in backup" -Level "WARNING"
            }
        }
        
        Write-Log "Restore completed successfully: $BackupName"
    } finally {
        # Start services after restore
        Start-CryptobotServices
        
        # Clean up temporary directory
        if (Test-Path -Path $TempDir) {
            Remove-Item -Path $TempDir -Recurse -Force
            Write-Log "Temporary directory removed"
        }
    }
    
} catch {
    $ErrorMessage = $_.Exception.Message
    Write-Log "Restore failed: $ErrorMessage" -Level "ERROR"
    
    # Ensure services are started even if restore fails
    Start-CryptobotServices
    
    exit 1
}