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
pip install -r ..\..\requirements.txt

# Install service-specific dependencies
Log "Installing service-specific dependencies..."

# Check if service-specific requirements files exist and install them
$services = @("auth", "strategy", "backtest", "trade", "data")

# foreach ($service in $services) {
#     $requirementsFile = "..\..\$service\requirements.txt"
#     if (Test-Path $requirementsFile) {
#         Log "Installing dependencies for $service service..."
#         pip install -r $requirementsFile
#     } else {
#         Log "Warning: No requirements.txt found for $service service."
#     }
# }

# Install development dependencies if available
# if (Test-Path "..\..\requirements-dev.txt") { # Corrected path in condition
#     Log "Installing development dependencies..."
#     pip install -r ..\..\requirements-dev.txt
# }

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

# Source the activation script (activates venv for this run_cryptobot.ps1 script's session)
# and loads .env variables into this session.
.\activate_env.ps1

# Define paths relative to this script (run_cryptobot.ps1)
`$ScriptRootForRunScript = `$PSScriptRoot
`$ProjectRootForRunScript = Resolve-Path "`$ScriptRootForRunScript\..\.." -ErrorAction SilentlyContinue
`$VenvActivatePathForRunScript = Resolve-Path "`$ScriptRootForRunScript\venv\Scripts\Activate.ps1" -ErrorAction SilentlyContinue

if (-not `$ProjectRootForRunScript) { Write-Error "Could not resolve Project Root from `$ScriptRootForRunScript\..\.."; exit 1 }
if (-not `$VenvActivatePathForRunScript) { Write-Error "Could not resolve Venv Activate Path from `$ScriptRootForRunScript\venv\Scripts\Activate.ps1"; exit 1 }

Write-Host "Project Root for services: `$ProjectRootForRunScript"
Write-Host "Venv Activate Path for services: `$VenvActivatePathForRunScript"
Write-Host "Starting Cryptobot services..."

# Function to start a service
function Start-CryptobotService {
    param (
        [string]`$ServiceName,
        [string]`$ServiceModule # e.g., auth, data
    )
    
    Write-Host "Starting `$ServiceName Service (module: `$ServiceModule)..."
    # Command to be run in the new PowerShell window:
    # 1. Change to Project Root
    # 2. Activate the virtual environment using its full path
    # 3. Run the service as a Python module
    `$ServiceCommand = "cd '`$ProjectRootForRunScript'; & '`$VenvActivatePathForRunScript'; python -m `$ServiceModule.main"
    
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", `$ServiceCommand
}

# Start Auth Service
Start-CryptobotService -ServiceName "Auth" -ServiceModule "auth"

# Start Strategy Service
Start-CryptobotService -ServiceName "Strategy" -ServiceModule "strategy"

# Start Backtest Service
Start-CryptobotService -ServiceName "Backtest" -ServiceModule "backtest"

# Start Trade Service
Start-CryptobotService -ServiceName "Trade" -ServiceModule "trade"

# Start Data Service
Start-CryptobotService -ServiceName "Data" -ServiceModule "data"

Write-Host "All services started!"
Write-Host "Close the new terminal windows to stop the individual services."
"@

Set-Content -Path "run_cryptobot.ps1" -Value $runContent

Log "Python environment setup completed successfully!"
Log "To activate the environment, run: .\activate_env.ps1"
Log "To start the application, run: .\run_cryptobot.ps1"

# Deactivate virtual environment
deactivate

exit 0