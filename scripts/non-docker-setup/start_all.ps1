# Master Startup Script for CryptoBot Services (Windows)

# Display banner
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  CryptoBot Services - Master Startup Script" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running with administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "Warning: This script is running with administrator privileges." -ForegroundColor Yellow
    Write-Host "It's recommended to run this script as a regular user." -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        Write-Host "Aborting."
        exit 1
    }
}

# Check for required dependencies
Write-Host "Checking dependencies..."
try {
    python --version | Out-Null
} catch {
    Write-Host "Python is required but not installed. Aborting." -ForegroundColor Red
    exit 1
}

try {
    pip --version | Out-Null
} catch {
    Write-Host "Pip is required but not installed. Aborting." -ForegroundColor Red
    exit 1
}

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# Load environment variables if .env file exists
if (Test-Path .env) {
    Write-Host "Loading environment variables from .env file"
    Get-Content .env | ForEach-Object {
        if (!$_.StartsWith("#") -and $_.Length -gt 0) {
            $key, $value = $_ -split '=', 2
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
} else {
    Write-Host "Warning: .env file not found. Using default environment variables." -ForegroundColor Yellow
}

# Start all services using the orchestration script
Write-Host "Starting all services..."
& .\scripts\non-docker-setup\orchestrate_services.ps1 start all

# Check if all services started successfully
Write-Host "Checking if all services are running..."
& .\scripts\non-docker-setup\orchestrate_services.ps1 status

# Set default values for environment variables if not set
if (-not $env:AUTH_HOST) { $env:AUTH_HOST = "0.0.0.0" }
if (-not $env:AUTH_PORT) { $env:AUTH_PORT = "8000" }
if (-not $env:DATA_HOST) { $env:DATA_HOST = "0.0.0.0" }
if (-not $env:DATA_PORT) { $env:DATA_PORT = "8001" }
if (-not $env:STRATEGY_HOST) { $env:STRATEGY_HOST = "0.0.0.0" }
if (-not $env:STRATEGY_PORT) { $env:STRATEGY_PORT = "8002" }
if (-not $env:BACKTEST_HOST) { $env:BACKTEST_HOST = "0.0.0.0" }
if (-not $env:BACKTEST_PORT) { $env:BACKTEST_PORT = "8003" }
if (-not $env:TRADE_HOST) { $env:TRADE_HOST = "0.0.0.0" }
if (-not $env:TRADE_PORT) { $env:TRADE_PORT = "8004" }

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  CryptoBot Services - Startup Complete" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services are now running with the following endpoints:"
Write-Host "- Auth Service:     http://$($env:AUTH_HOST):$($env:AUTH_PORT)"
Write-Host "- Data Service:     http://$($env:DATA_HOST):$($env:DATA_PORT)"
Write-Host "- Strategy Service: http://$($env:STRATEGY_HOST):$($env:STRATEGY_PORT)"
Write-Host "- Backtest Service: http://$($env:BACKTEST_HOST):$($env:BACKTEST_PORT)"
Write-Host "- Trade Service:    http://$($env:TRADE_HOST):$($env:TRADE_PORT)"
Write-Host ""
Write-Host "To stop all services, run: .\scripts\non-docker-setup\orchestrate_services.ps1 stop all"
Write-Host "To check service status, run: .\scripts\non-docker-setup\orchestrate_services.ps1 status"
Write-Host ""