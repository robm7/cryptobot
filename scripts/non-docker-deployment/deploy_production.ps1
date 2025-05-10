<#
.SYNOPSIS
    Production deployment script for Cryptobot non-Docker installation.
.DESCRIPTION
    This script performs a complete production deployment of the Cryptobot application.
    It includes steps for backup, configuration, service deployment, and verification.
.NOTES
    File Name      : deploy_production.ps1
    Prerequisite   : PowerShell 5.1 or later
#>

# Stop on any error
$ErrorActionPreference = "Stop"

# Script variables
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootPath = (Get-Item $ScriptPath).Parent.Parent.FullName
$ConfigPath = Join-Path -Path $RootPath -ChildPath "config\non-docker"
$LogPath = Join-Path -Path $RootPath -ChildPath "logs"
$BackupPath = Join-Path -Path $RootPath -ChildPath "backups"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path -Path $LogPath -ChildPath "deployment_$Timestamp.log"

# Create log directory if it doesn't exist
if (-not (Test-Path -Path $LogPath)) {
    New-Item -Path $LogPath -ItemType Directory -Force | Out-Null
}

# Create backup directory if it doesn't exist
if (-not (Test-Path -Path $BackupPath)) {
    New-Item -Path $BackupPath -ItemType Directory -Force | Out-Null
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

# Function to run a script and check its exit code
function Invoke-Script {
    param (
        [Parameter(Mandatory=$true)]
        [string]$ScriptPath,
        
        [Parameter(Mandatory=$false)]
        [string]$Description = ""
    )
    
    if (-not (Test-Path -Path $ScriptPath)) {
        Write-Log "Script not found: $ScriptPath" -Level "ERROR"
        exit 1
    }
    
    Write-Log "Running: $Description"
    & $ScriptPath
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Script failed with exit code $LASTEXITCODE: $ScriptPath" -Level "ERROR"
        exit $LASTEXITCODE
    }
}

# Main deployment process
try {
    Write-Log "Starting production deployment of Cryptobot"
    Write-Log "Deployment timestamp: $Timestamp"
    
    # 1. Verify system requirements
    Write-Log "Verifying system requirements"
    $RequirementsScript = Join-Path -Path $ScriptPath -ChildPath "..\non-docker-setup\setup_base_system.ps1"
    Invoke-Script -ScriptPath $RequirementsScript -Description "System requirements verification"
    
    # 2. Create backup before deployment
    Write-Log "Creating pre-deployment backup"
    $BackupScript = Join-Path -Path $ScriptPath -ChildPath "backup.ps1"
    $BackupName = "pre_deployment_$Timestamp"
    & $BackupScript -BackupName $BackupName
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Backup failed with exit code $LASTEXITCODE" -Level "ERROR"
        exit $LASTEXITCODE
    }
    
    # 3. Stop all services
    Write-Log "Stopping all services"
    $StopScript = Join-Path -Path $RootPath -ChildPath "scripts\non-docker-setup\stop_all.ps1"
    if (Test-Path -Path $StopScript) {
        Invoke-Script -ScriptPath $StopScript -Description "Stopping all services"
    } else {
        Write-Log "Stop script not found, attempting to stop services manually" -Level "WARNING"
        Get-Service -Name "Cryptobot*" -ErrorAction SilentlyContinue | Stop-Service
    }
    
    # 4. Update configuration
    Write-Log "Updating configuration"
    $ConfigScript = Join-Path -Path $ScriptPath -ChildPath "..\non-docker-setup\config_migration.ps1"
    Invoke-Script -ScriptPath $ConfigScript -Description "Configuration update"
    
    # 5. Apply security hardening
    Write-Log "Applying security hardening"
    $SecurityScript = Join-Path -Path $ScriptPath -ChildPath "..\non-docker-security\secure_config.ps1"
    Invoke-Script -ScriptPath $SecurityScript -Description "Security hardening"
    
    # 6. Update services
    Write-Log "Updating services"
    $ServicesScript = Join-Path -Path $ScriptPath -ChildPath "..\non-docker-setup\install_services.ps1"
    Invoke-Script -ScriptPath $ServicesScript -Description "Services update"
    
    # 7. Set up monitoring
    Write-Log "Setting up monitoring"
    $MonitoringScript = Join-Path -Path $ScriptPath -ChildPath "setup_monitoring.ps1"
    Invoke-Script -ScriptPath $MonitoringScript -Description "Monitoring setup"
    
    # 8. Set up logging
    Write-Log "Setting up logging"
    $LoggingScript = Join-Path -Path $ScriptPath -ChildPath "setup_logging.ps1"
    Invoke-Script -ScriptPath $LoggingScript -Description "Logging setup"
    
    # 9. Set up alerting
    Write-Log "Setting up alerting"
    $AlertingScript = Join-Path -Path $ScriptPath -ChildPath "setup_alerts.ps1"
    Invoke-Script -ScriptPath $AlertingScript -Description "Alerting setup"
    
    # 10. Start all services
    Write-Log "Starting all services"
    $StartScript = Join-Path -Path $RootPath -ChildPath "scripts\non-docker-setup\start_all.ps1"
    Invoke-Script -ScriptPath $StartScript -Description "Starting all services"
    
    # 11. Run verification tests
    Write-Log "Running verification tests"
    $TestScript = Join-Path -Path $RootPath -ChildPath "scripts\non-docker-tests\run_all_tests.ps1"
    Invoke-Script -ScriptPath $TestScript -Description "Verification tests"
    
    # 12. Verify monitoring is working
    Write-Log "Verifying monitoring"
    $MonitoringVerifyScript = Join-Path -Path $ScriptPath -ChildPath "verify_monitoring.ps1"
    if (Test-Path -Path $MonitoringVerifyScript) {
        Invoke-Script -ScriptPath $MonitoringVerifyScript -Description "Monitoring verification"
    } else {
        Write-Log "Monitoring verification script not found, skipping" -Level "WARNING"
    }
    
    Write-Log "Deployment completed successfully"
    
} catch {
    $ErrorMessage = $_.Exception.Message
    Write-Log "Deployment failed: $ErrorMessage" -Level "ERROR"
    
    # Attempt to restore from backup
    Write-Log "Attempting to restore from backup" -Level "WARNING"
    $RestoreScript = Join-Path -Path $ScriptPath -ChildPath "restore.ps1"
    & $RestoreScript -BackupName $BackupName
    
    exit 1
}