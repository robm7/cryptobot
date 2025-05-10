# PowerShell script to start Cryptobot services
# This script demonstrates how to start Cryptobot services on Windows

# Set environment variables
$env:CRYPTOBOT_ENV = "development"
$env:CRYPTOBOT_LOG_LEVEL = "INFO"

# Function to print colored status messages
function Write-Status {
    param (
        [string]$status,
        [string]$message
    )
    
    switch ($status) {
        "success" { Write-Host "[SUCCESS] $message" -ForegroundColor Green }
        "warning" { Write-Host "[WARNING] $message" -ForegroundColor Yellow }
        "error" { Write-Host "[ERROR] $message" -ForegroundColor Red }
        "info" { Write-Host "[INFO] $message" -ForegroundColor Cyan }
        default { Write-Host "$message" }
    }
}

# Function to check if a port is available
function Test-Port {
    param (
        [int]$port
    )
    
    $result = $null
    $result = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    
    if ($result) {
        return $false
    } else {
        return $true
    }
}

# Function to start a service
function Start-CryptobotService {
    param (
        [string]$serviceName,
        [int]$port
    )
    
    Write-Status -status "info" -message "Starting $serviceName service on port $port..."
    
    # Check if port is available
    if (-not (Test-Port -port $port)) {
        Write-Status -status "error" -message "Port $port is already in use. Cannot start $serviceName service."
        return $false
    }
    
    # Start the service
    $process = Start-Process -FilePath "cryptobot" -ArgumentList "--service $serviceName" -PassThru -WindowStyle Hidden
    
    # Wait for service to start
    Start-Sleep -Seconds 2
    
    # Check if service is running
    if (-not $process.HasExited) {
        Write-Status -status "success" -message "$serviceName service started successfully (PID: $($process.Id))"
        $process.Id | Out-File -FilePath "$env:TEMP\cryptobot_${serviceName}.pid"
        return $true
    } else {
        Write-Status -status "error" -message "Failed to start $serviceName service"
        return $false
    }
}

# Function to check service health
function Test-ServiceHealth {
    param (
        [string]$serviceName,
        [int]$port
    )
    
    Write-Status -status "info" -message "Checking health of $serviceName service..."
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$port/health" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
        
        if ($response.StatusCode -eq 200) {
            Write-Status -status "success" -message "$serviceName service is healthy"
            return $true
        } else {
            Write-Status -status "warning" -message "$serviceName service health check failed (HTTP $($response.StatusCode))"
            return $false
        }
    } catch {
        Write-Status -status "warning" -message "$serviceName service health check failed: $_"
        return $false
    }
}

# Main script

# Print banner
Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Cryptobot Services Startup Script" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Check if cryptobot command is available
try {
    $null = Get-Command cryptobot -ErrorAction Stop
} catch {
    Write-Status -status "error" -message "cryptobot command not found. Please make sure Cryptobot is installed correctly."
    exit 1
}

# Create data directories if they don't exist
if (-not (Test-Path -Path "data\logs")) {
    New-Item -Path "data\logs" -ItemType Directory -Force | Out-Null
}

if (-not (Test-Path -Path "data\db")) {
    New-Item -Path "data\db" -ItemType Directory -Force | Out-Null
}

Write-Status -status "info" -message "Starting Cryptobot services..."

# Start services
$authStatus = Start-CryptobotService -serviceName "auth" -port 8000
$strategyStatus = Start-CryptobotService -serviceName "strategy" -port 8001
$dataStatus = Start-CryptobotService -serviceName "data" -port 8002
$tradeStatus = Start-CryptobotService -serviceName "trade" -port 8003
$backtestStatus = Start-CryptobotService -serviceName "backtest" -port 8004

# Wait for services to initialize
Write-Status -status "info" -message "Waiting for services to initialize..."
Start-Sleep -Seconds 5

# Check service health
if ($authStatus) {
    Test-ServiceHealth -serviceName "auth" -port 8000
}

if ($strategyStatus) {
    Test-ServiceHealth -serviceName "strategy" -port 8001
}

if ($dataStatus) {
    Test-ServiceHealth -serviceName "data" -port 8002
}

if ($tradeStatus) {
    Test-ServiceHealth -serviceName "trade" -port 8003
}

if ($backtestStatus) {
    Test-ServiceHealth -serviceName "backtest" -port 8004
}

# Start dashboard
Write-Status -status "info" -message "Starting dashboard..."
if (Test-Port -port 8080) {
    $dashboardProcess = Start-Process -FilePath "cryptobot" -ArgumentList "--service dashboard" -PassThru -WindowStyle Hidden
    $dashboardProcess.Id | Out-File -FilePath "$env:TEMP\cryptobot_dashboard.pid"
    Write-Status -status "success" -message "Dashboard started successfully (PID: $($dashboardProcess.Id))"
    Write-Status -status "info" -message "Dashboard available at: http://localhost:8080"
} else {
    Write-Status -status "error" -message "Port 8080 is already in use. Cannot start dashboard."
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Cryptobot Services Status Summary" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue

$services = @(
    @{Name="auth"; Port=8000},
    @{Name="strategy"; Port=8001},
    @{Name="data"; Port=8002},
    @{Name="trade"; Port=8003},
    @{Name="backtest"; Port=8004},
    @{Name="dashboard"; Port=8080}
)

foreach ($service in $services) {
    $pidFile = "$env:TEMP\cryptobot_$($service.Name).pid"
    
    if (Test-Path -Path $pidFile) {
        $pid = Get-Content -Path $pidFile
        try {
            $process = Get-Process -Id $pid -ErrorAction Stop
            Write-Status -status "success" -message "$($service.Name) service is running on port $($service.Port) (PID: $pid)"
        } catch {
            Write-Status -status "error" -message "$($service.Name) service is not running"
        }
    } else {
        Write-Status -status "error" -message "$($service.Name) service was not started"
    }
}

Write-Host ""
Write-Status -status "info" -message "To stop all services, run: .\stop_services.ps1"
Write-Status -status "info" -message "To view logs, check the data\logs directory"

# Open dashboard in browser
Write-Status -status "info" -message "Opening dashboard in default browser..."
Start-Process "http://localhost:8080"