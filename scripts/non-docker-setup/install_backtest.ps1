# Cryptobot Backtest Service Installation Script for Windows

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

# Create service directory if it doesn't exist
$ServiceDir = "C:\Program Files\Cryptobot\services\backtest"
Log "Creating service directory at $ServiceDir"
New-Item -ItemType Directory -Force -Path $ServiceDir | Out-Null

# Copy service files
Log "Copying backtest service files..."
Copy-Item -Path ".\backtest\*" -Destination $ServiceDir -Recurse -Force

# Install dependencies
Log "Installing backtest service dependencies..."
if (Test-Path "$ServiceDir\requirements.txt") {
    # Check if we're in a virtual environment
    if (-not $env:VIRTUAL_ENV) {
        Log "Warning: Not running in a virtual environment. It's recommended to activate the virtual environment first."
        $continue = Read-Host "Continue anyway? (y/n)"
        if ($continue -ne "y") {
            Log "Please activate the virtual environment and try again."
            exit 1
        }
    }
    
    pip install -r "$ServiceDir\requirements.txt"
}
else {
    Log "Warning: requirements.txt not found for backtest service. Using project requirements."
    pip install -r ".\requirements.txt"
}

# Create service configuration
Log "Setting up backtest service configuration..."
$ConfigDir = "C:\ProgramData\Cryptobot\backtest"
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

# Check if config file exists from Phase 3
if (Test-Path ".\config\backtest_service_config.json") {
    Copy-Item -Path ".\config\backtest_service_config.json" -Destination "$ConfigDir\config.json" -Force
    Log "Copied configuration from Phase 3 setup."
}
else {
    Log "Warning: Configuration file from Phase 3 not found. Using default configuration."
    # Create a default config file
    $defaultConfig = @"
{
    "service_name": "backtest",
    "host": "0.0.0.0",
    "port": 8002,
    "log_level": "info",
    "database": {
        "host": "localhost",
        "port": 5432,
        "username": "cryptobot",
        "password": "changeme",
        "database": "cryptobot"
    },
    "auth_service": {
        "url": "http://localhost:8000",
        "api_key": "CHANGE_THIS_TO_A_SECURE_API_KEY"
    },
    "data_service": {
        "url": "http://localhost:8003"
    },
    "strategy_service": {
        "url": "http://localhost:8001"
    },
    "results_dir": "C:\\ProgramData\\Cryptobot\\backtest_results"
}
"@
    $defaultConfig | Out-File -FilePath "$ConfigDir\config.json" -Encoding utf8
    Log "Created default configuration. Please update with secure values."
}

# Create a symbolic link to the configuration (Windows uses junction points)
cmd /c mklink /J "$ServiceDir\config.json" "$ConfigDir\config.json"

# Create results directory
$ResultsDir = "C:\ProgramData\Cryptobot\backtest_results"
New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null

# Set up Windows service
Log "Setting up Windows service for backtest service..."

# Check if NSSM (Non-Sucking Service Manager) is installed
$nssmPath = "C:\Program Files\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    Log "NSSM (Non-Sucking Service Manager) is required to create Windows services."
    Log "Downloading NSSM..."
    
    # Create a temporary directory
    $tempDir = [System.IO.Path]::GetTempPath() + [System.Guid]::NewGuid().ToString()
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    
    # Download NSSM
    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $nssmZip = "$tempDir\nssm.zip"
    Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
    
    # Extract NSSM
    Expand-Archive -Path $nssmZip -DestinationPath $tempDir
    
    # Create NSSM directory
    New-Item -ItemType Directory -Force -Path "C:\Program Files\nssm" | Out-Null
    
    # Copy NSSM executable
    Copy-Item -Path "$tempDir\nssm-2.24\win64\nssm.exe" -Destination $nssmPath -Force
    
    # Clean up
    Remove-Item -Path $tempDir -Recurse -Force
    
    Log "NSSM has been installed."
}

# Create a batch file to run the service
$batchFile = "$ServiceDir\run_service.bat"
@"
@echo off
cd /d "%~dp0"
set PYTHONPATH=%PYTHONPATH%;%CD%
python main.py
"@ | Out-File -FilePath $batchFile -Encoding ascii

# Create the Windows service using NSSM
& $nssmPath install CryptobotBacktest "$batchFile"
& $nssmPath set CryptobotBacktest DisplayName "Cryptobot Backtest Service"
& $nssmPath set CryptobotBacktest Description "Backtesting service for Cryptobot"
& $nssmPath set CryptobotBacktest AppDirectory "$ServiceDir"
& $nssmPath set CryptobotBacktest AppStdout "$ServiceDir\service.log"
& $nssmPath set CryptobotBacktest AppStderr "$ServiceDir\service.err"
& $nssmPath set CryptobotBacktest Start SERVICE_AUTO_START
& $nssmPath set CryptobotBacktest ObjectName LocalSystem

# Set service dependencies
& $nssmPath set CryptobotBacktest DependOnService postgresql-x64-14 CryptobotAuth CryptobotStrategy

Log "Backtest service has been installed and configured as a Windows service."
Log "To start the service, run: Start-Service CryptobotBacktest"

# Create a simple script to run the service manually
$runScript = @"
@echo off
cd /d "%~dp0"
set PYTHONPATH=%PYTHONPATH%;%CD%
python main.py
"@
$runScript | Out-File -FilePath "$ServiceDir\run_service.bat" -Encoding ascii

Log "Backtest service installation completed successfully!"
Log "You can manually start the service by running: $ServiceDir\run_service.bat"

exit 0