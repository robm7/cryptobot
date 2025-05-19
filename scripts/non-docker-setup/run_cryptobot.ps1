# Cryptobot Run Script
# This script activates the virtual environment and starts the Cryptobot services

# Source the activation script (activates venv for this run_cryptobot.ps1 script's session)
# and loads .env variables into this session.
.\activate_env.ps1

# Define paths relative to this script (run_cryptobot.ps1)
$ScriptRootForRunScript = $PSScriptRoot
$ProjectRootForRunScript = Resolve-Path "$ScriptRootForRunScript\..\.." -ErrorAction SilentlyContinue
$VenvActivatePathForRunScript = Resolve-Path "$ScriptRootForRunScript\venv\Scripts\Activate.ps1" -ErrorAction SilentlyContinue

if (-not $ProjectRootForRunScript) { Write-Error "Could not resolve Project Root from $ScriptRootForRunScript\..\.."; exit 1 }
if (-not $VenvActivatePathForRunScript) { Write-Error "Could not resolve Venv Activate Path from $ScriptRootForRunScript\venv\Scripts\Activate.ps1"; exit 1 }

Write-Host "Project Root for services: $ProjectRootForRunScript"
Write-Host "Venv Activate Path for services: $VenvActivatePathForRunScript"
Write-Host "Starting Cryptobot services..."

# Function to start a service
function Start-CryptobotService {
    param (
        [string]$ServiceName,
        [string]$ServiceModule # e.g., auth, data
    )
    
    Write-Host "Starting $ServiceName Service (module: $ServiceModule)..."
    # Command to be run in the new PowerShell window:
    # 1. Change to Project Root
    # 2. Activate the virtual environment using its full path
    # 3. Run the service as a Python module
    $ServiceCommand = "cd '$ProjectRootForRunScript'; & '$VenvActivatePathForRunScript'; python -m $ServiceModule.main"
    
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", $ServiceCommand
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
