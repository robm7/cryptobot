# PowerShell script to install CryptoBot services as Windows Services
# Must be run as Administrator

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "This script must be run as Administrator. Please restart PowerShell as Administrator and try again." -ForegroundColor Red
    exit 1
}

# Check if NSSM (Non-Sucking Service Manager) is installed
$nssmPath = "C:\Program Files\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    Write-Host "NSSM (Non-Sucking Service Manager) is required but not found at $nssmPath." -ForegroundColor Red
    Write-Host "Please download and install NSSM from https://nssm.cc/download" -ForegroundColor Yellow
    Write-Host "After installing, run this script again." -ForegroundColor Yellow
    exit 1
}

# Configuration
$installDir = "C:\CryptoBot"
$pythonPath = "C:\Python39\python.exe"
$logDir = "$installDir\logs"

# Create log directory if it doesn't exist
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
    Write-Host "Created log directory: $logDir" -ForegroundColor Green
}

# Function to install a service
function Install-CryptoBotService {
    param (
        [string]$ServiceName,
        [string]$DisplayName,
        [string]$Description,
        [string]$Module,
        [int]$Port,
        [int]$Workers,
        [string[]]$Dependencies = @()
    )
    
    Write-Host "Installing $DisplayName..." -ForegroundColor Cyan
    
    # Check if service already exists
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Write-Host "Service $ServiceName already exists. Stopping and removing..." -ForegroundColor Yellow
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        & $nssmPath remove $ServiceName confirm
    }
    
    # Create the service
    $arguments = "-m uvicorn $Module.main:app --host 0.0.0.0 --port $Port --workers $Workers"
    
    & $nssmPath install $ServiceName $pythonPath $arguments
    & $nssmPath set $ServiceName DisplayName $DisplayName
    & $nssmPath set $ServiceName Description $Description
    & $nssmPath set $ServiceName AppDirectory $installDir
    & $nssmPath set $ServiceName AppEnvironmentExtra "PYTHONPATH=$installDir"
    & $nssmPath set $ServiceName AppStdout "$logDir\${ServiceName}_stdout.log"
    & $nssmPath set $ServiceName AppStderr "$logDir\${ServiceName}_stderr.log"
    & $nssmPath set $ServiceName AppRotateFiles 1
    & $nssmPath set $ServiceName AppRotateOnline 1
    & $nssmPath set $ServiceName AppRotateSeconds 86400
    & $nssmPath set $ServiceName AppRotateBytes 10485760
    
    # Set dependencies if any
    if ($Dependencies.Count -gt 0) {
        $dependencyString = $Dependencies -join "/"
        & $nssmPath set $ServiceName DependOnService $dependencyString
    }
    
    Write-Host "$DisplayName installed successfully." -ForegroundColor Green
}

# Install Auth Service
Install-CryptoBotService -ServiceName "CryptoBotAuth" `
                         -DisplayName "CryptoBot Auth Service" `
                         -Description "Authentication service for CryptoBot" `
                         -Module "auth" `
                         -Port 8000 `
                         -Workers 4

# Install Data Service
Install-CryptoBotService -ServiceName "CryptoBotData" `
                         -DisplayName "CryptoBot Data Service" `
                         -Description "Data service for CryptoBot" `
                         -Module "data" `
                         -Port 8001 `
                         -Workers 2 `
                         -Dependencies @("CryptoBotAuth")

# Install Strategy Service
Install-CryptoBotService -ServiceName "CryptoBotStrategy" `
                         -DisplayName "CryptoBot Strategy Service" `
                         -Description "Strategy service for CryptoBot" `
                         -Module "strategy" `
                         -Port 8002 `
                         -Workers 2 `
                         -Dependencies @("CryptoBotAuth", "CryptoBotData")

# Install Backtest Service
Install-CryptoBotService -ServiceName "CryptoBotBacktest" `
                         -DisplayName "CryptoBot Backtest Service" `
                         -Description "Backtest service for CryptoBot" `
                         -Module "backtest" `
                         -Port 8003 `
                         -Workers 2 `
                         -Dependencies @("CryptoBotAuth", "CryptoBotData", "CryptoBotStrategy")

# Install Trade Service
Install-CryptoBotService -ServiceName "CryptoBotTrade" `
                         -DisplayName "CryptoBot Trade Service" `
                         -Description "Trade service for CryptoBot" `
                         -Module "trade" `
                         -Port 8004 `
                         -Workers 2 `
                         -Dependencies @("CryptoBotAuth", "CryptoBotStrategy")

Write-Host "All CryptoBot services have been installed." -ForegroundColor Green
Write-Host "You can start/stop/manage them using the Windows Services management console." -ForegroundColor Cyan
Write-Host "To open the Services console, run: services.msc" -ForegroundColor Cyan