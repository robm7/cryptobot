<#
.SYNOPSIS
    Backup script for Cryptobot non-Docker installation.
.DESCRIPTION
    This script creates a backup of the Cryptobot application, including configuration, database, and logs.
    It can be used for regular backups or before making significant changes to the system.
.PARAMETER BackupName
    The name of the backup. If not provided, a timestamp will be used.
.PARAMETER IncludeLogs
    Whether to include logs in the backup. Default is false.
.PARAMETER BackupDir
    The directory to store backups. Default is "backups" in the root directory.
.NOTES
    File Name      : backup.ps1
    Prerequisite   : PowerShell 5.1 or later
.EXAMPLE
    .\backup.ps1 -BackupName "pre_upgrade"
    Creates a backup named "pre_upgrade".
.EXAMPLE
    .\backup.ps1 -IncludeLogs
    Creates a backup with a timestamp name and includes logs.
#>

param (
    [string]$BackupName,
    [switch]$IncludeLogs = $false,
    [string]$BackupDir
)

# Stop on any error
$ErrorActionPreference = "Stop"

# Script variables
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootPath = (Get-Item $ScriptPath).Parent.Parent.FullName
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path -Path $RootPath -ChildPath "logs"
$LogFile = Join-Path -Path $LogPath -ChildPath "backup_$Timestamp.log"

# Create log directory if it doesn't exist
if (-not (Test-Path -Path $LogPath)) {
    New-Item -Path $LogPath -ItemType Directory -Force | Out-Null
}

# Set backup directory
if (-not $BackupDir) {
    $BackupDir = Join-Path -Path $RootPath -ChildPath "backups"
}

# Create backup directory if it doesn't exist
if (-not (Test-Path -Path $BackupDir)) {
    New-Item -Path $BackupDir -ItemType Directory -Force | Out-Null
}

# Set backup name
if (-not $BackupName) {
    $BackupName = "backup_$Timestamp"
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

# Main backup process
try {
    Write-Log "Starting backup process: $BackupName"
    
    # Create backup directory
    $BackupPath = Join-Path -Path $BackupDir -ChildPath $BackupName
    if (Test-Path -Path $BackupPath) {
        Write-Log "Backup directory already exists: $BackupPath" -Level "WARNING"
        $Confirm = Read-Host "Backup directory already exists. Do you want to overwrite it? (Y/N)"
        if ($Confirm -ne "Y") {
            Write-Log "Backup aborted by user" -Level "WARNING"
            exit 0
        }
        Remove-Item -Path $BackupPath -Recurse -Force
    }
    
    New-Item -Path $BackupPath -ItemType Directory -Force | Out-Null
    Write-Log "Created backup directory: $BackupPath"
    
    # Stop services before backup
    Stop-CryptobotServices
    
    try {
        # 1. Backup configuration
        Write-Log "Backing up configuration"
        $ConfigDir = Join-Path -Path $RootPath -ChildPath "config"
        $ConfigBackupDir = Join-Path -Path $BackupPath -ChildPath "config"
        
        if (Test-Path -Path $ConfigDir) {
            New-Item -Path $ConfigBackupDir -ItemType Directory -Force | Out-Null
            Copy-Item -Path "$ConfigDir\*" -Destination $ConfigBackupDir -Recurse -Force
            Write-Log "Configuration backed up to: $ConfigBackupDir"
        } else {
            Write-Log "Configuration directory not found: $ConfigDir" -Level "WARNING"
        }
        
        # 2. Backup database
        Write-Log "Backing up database"
        $DbBackupDir = Join-Path -Path $BackupPath -ChildPath "database"
        New-Item -Path $DbBackupDir -ItemType Directory -Force | Out-Null
        
        # Check if PostgreSQL is installed
        $PgDumpExists = Test-CommandExists -Command "pg_dump"
        if ($PgDumpExists) {
            Write-Log "PostgreSQL detected, using pg_dump"
            
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
            
            # Set PGPASSWORD environment variable for pg_dump
            $env:PGPASSWORD = $DbPassword
            
            # Dump database
            $DbDumpFile = Join-Path -Path $DbBackupDir -ChildPath "$DbName.sql"
            & pg_dump -h $DbHost -p $DbPort -U $DbUser -F c -b -v -f $DbDumpFile $DbName
            
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Database backed up to: $DbDumpFile"
            } else {
                Write-Log "Database backup failed with exit code: $LASTEXITCODE" -Level "ERROR"
            }
            
            # Clear PGPASSWORD environment variable
            Remove-Item Env:\PGPASSWORD
        } else {
            # Check if SQLite is used
            $SqliteDbPath = Join-Path -Path $RootPath -ChildPath "database\cryptobot.db"
            if (Test-Path -Path $SqliteDbPath) {
                Write-Log "SQLite database detected, copying file"
                Copy-Item -Path $SqliteDbPath -Destination $DbBackupDir -Force
                Write-Log "SQLite database backed up to: $DbBackupDir\cryptobot.db"
            } else {
                Write-Log "No database found, skipping database backup" -Level "WARNING"
            }
        }
        
        # 3. Backup historical data
        Write-Log "Backing up historical data"
        $DataDir = Join-Path -Path $RootPath -ChildPath "data"
        $DataBackupDir = Join-Path -Path $BackupPath -ChildPath "data"
        
        if (Test-Path -Path $DataDir) {
            New-Item -Path $DataBackupDir -ItemType Directory -Force | Out-Null
            Copy-Item -Path "$DataDir\*" -Destination $DataBackupDir -Recurse -Force
            Write-Log "Historical data backed up to: $DataBackupDir"
        } else {
            Write-Log "Historical data directory not found: $DataDir" -Level "WARNING"
        }
        
        # 4. Backup logs (optional)
        if ($IncludeLogs) {
            Write-Log "Backing up logs"
            $LogsBackupDir = Join-Path -Path $BackupPath -ChildPath "logs"
            
            if (Test-Path -Path $LogPath) {
                New-Item -Path $LogsBackupDir -ItemType Directory -Force | Out-Null
                Copy-Item -Path "$LogPath\*" -Destination $LogsBackupDir -Recurse -Force
                Write-Log "Logs backed up to: $LogsBackupDir"
            } else {
                Write-Log "Logs directory not found: $LogPath" -Level "WARNING"
            }
        }
        
        # 5. Create backup metadata
        Write-Log "Creating backup metadata"
        $MetadataFile = Join-Path -Path $BackupPath -ChildPath "metadata.json"
        
        $Metadata = @{
            BackupName = $BackupName
            Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            IncludeLogs = $IncludeLogs.ToString()
            Version = "1.0"
            System = @{
                ComputerName = $env:COMPUTERNAME
                OSVersion = [System.Environment]::OSVersion.VersionString
                PowerShellVersion = $PSVersionTable.PSVersion.ToString()
            }
        }
        
        $Metadata | ConvertTo-Json -Depth 10 | Set-Content -Path $MetadataFile
        Write-Log "Backup metadata created: $MetadataFile"
        
        # 6. Create backup archive
        Write-Log "Creating backup archive"
        $BackupArchive = "$BackupPath.zip"
        
        if (Test-Path -Path $BackupArchive) {
            Remove-Item -Path $BackupArchive -Force
        }
        
        Compress-Archive -Path "$BackupPath\*" -DestinationPath $BackupArchive
        Write-Log "Backup archive created: $BackupArchive"
        
        # 7. Clean up temporary backup directory
        Remove-Item -Path $BackupPath -Recurse -Force
        Write-Log "Temporary backup directory removed"
        
        Write-Log "Backup completed successfully: $BackupName"
    } finally {
        # Start services after backup
        Start-CryptobotServices
    }
    
} catch {
    $ErrorMessage = $_.Exception.Message
    Write-Log "Backup failed: $ErrorMessage" -Level "ERROR"
    
    # Ensure services are started even if backup fails
    Start-CryptobotServices
    
    exit 1
}