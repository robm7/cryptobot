# Cryptobot Python Environment Setup Script for Windows
# This script sets up a Python virtual environment and installs all required dependencies

# Function to display messages
function Log {
    param (
        [string]$Message
    )
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
}

Log "Starting Python environment setup for Cryptobot..."

# Check if Python is installed
$pythonInstalled = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonInstalled) {
    Log "Error: Python is not installed. Please run setup_base_system.ps1 first."
    exit 1
}

# Check Python version
$pythonVersion = python --version
$pythonVersionMatch = $pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)"
if ($pythonVersionMatch) {
    $pythonMajor = [int]$Matches[1]
    $pythonMinor = [int]$Matches[2]
    
    Log "Detected Python version: $pythonMajor.$pythonMinor.$($Matches[3])"
    
    if ($pythonMajor -lt 3 -or ($pythonMajor -eq 3 -and $pythonMinor -lt 8)) {
        Log "Error: Python 3.8 or higher is required. Please upgrade your Python installation."
        exit 1
    }
} else {
    Log "Error: Could not determine Python version."
    exit 1
}

# Create virtual environment
Log "Creating Python virtual environment..."
python -m venv venv

# Activate virtual environment
Log "Activating virtual environment..."
$activateScript = ".\venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
} else {
    Log "Error: Virtual environment activation script not found at $activateScript"
    exit 1
}

# Upgrade pip
Log "Upgrading pip..."
python -m pip install --upgrade pip

# Install core dependencies
Log "Installing core dependencies..."
pip install -r requirements.txt

# Install service-specific dependencies
Log "Installing service-specific dependencies..."

# Check if service-specific requirements files exist and install them
$services = @("auth", "strategy", "backtest", "trade", "data")

foreach ($service in $services) {
    $requirementsFile = "$service\requirements.txt"
    if (Test-Path $requirementsFile) {
        Log "Installing dependencies for $service service..."
        pip install -r $requirementsFile
    } else {
        Log "Warning: No requirements.txt found for $service service."
    }
}

# Install development dependencies if available
if (Test-Path "requirements-dev.txt") {
    Log "Installing development dependencies..."
    pip install -r requirements-dev.txt
}

# Create a script to activate the virtual environment
Log "Creating activation script..."
$activateContent = @"
# Cryptobot Environment Activation Script
# Run this script to activate the Python virtual environment

Write-Host "Activating Cryptobot Python virtual environment..."
.\venv\Scripts\Activate.ps1

# Set environment variables
if (Test-Path .env) {
    Write-Host "Loading environment variables from .env file..."
    Get-Content .env | ForEach-Object {
        if (`$_ -match '^([^#][^=]*)=(.*)$') {
            `$key = `$matches[1].Trim()
            `$value = `$matches[2].Trim()
            Set-Variable -Name `$key -Value `$value -Scope Global
            [Environment]::SetEnvironmentVariable(`$key, `$value, 'Process')
        }
    }
}

Write-Host "Cryptobot environment activated!"
Write-Host "Run 'deactivate' to exit the virtual environment."
"@

Set-Content -Path "activate_env.ps1" -Value $activateContent

# Create a script to run the application
Log "Creating run script..."
$runContent = @"
# Cryptobot Run Script
# This script activates the virtual environment and starts the Cryptobot services

# Source the activation script
.\activate_env.ps1

# Start the services
Write-Host "Starting Cryptobot services..."

# Function to start a service
function Start-CryptobotService {
    param (
        [string]`$ServiceName,
        [string]`$Directory
    )
    
    Write-Host "Starting `$ServiceName Service..."
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd `$Directory; .\venv\Scripts\Activate.ps1; python main.py"
}

# Start Auth Service
Start-CryptobotService -ServiceName "Auth" -Directory "`$PWD\auth"

# Start Strategy Service
Start-CryptobotService -ServiceName "Strategy" -Directory "`$PWD\strategy"

# Start Backtest Service
Start-CryptobotService -ServiceName "Backtest" -Directory "`$PWD\backtest"

# Start Trade Service
Start-CryptobotService -ServiceName "Trade" -Directory "`$PWD\trade"

# Start Data Service
Start-CryptobotService -ServiceName "Data" -Directory "`$PWD\data"

Write-Host "All services started!"
Write-Host "Close the terminal windows to stop the services."
"@

Set-Content -Path "run_cryptobot.ps1" -Value $runContent

Log "Python environment setup completed successfully!"
Log "To activate the environment, run: .\activate_env.ps1"
Log "To start the application, run: .\run_cryptobot.ps1"

# Deactivate virtual environment
deactivate

exit 0