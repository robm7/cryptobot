# Trade Service Startup Script for Windows

# Load environment variables if .env file exists
if (Test-Path .env) {
    Write-Host "Loading environment variables from .env file"
    Get-Content .env | ForEach-Object {
        if (!$_.StartsWith("#") -and $_.Length -gt 0) {
            $key, $value = $_ -split '=', 2
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Check for required dependencies
try {
    python --version | Out-Null
} catch {
    Write-Host "Python is required but not installed. Aborting."
    exit 1
}

try {
    pip --version | Out-Null
} catch {
    Write-Host "Pip is required but not installed. Aborting."
    exit 1
}

# Set default values for environment variables if not set
if (-not $env:TRADE_HOST) { $env:TRADE_HOST = "0.0.0.0" }
if (-not $env:TRADE_PORT) { $env:TRADE_PORT = "8004" }
if (-not $env:TRADE_WORKERS) { $env:TRADE_WORKERS = "2" }
if (-not $env:TRADE_LOG_LEVEL) { $env:TRADE_LOG_LEVEL = "info" }
if (-not $env:TRADE_DB_URL) { $env:TRADE_DB_URL = "sqlite:///./trade.db" }
if (-not $env:AUTH_HOST) { $env:AUTH_HOST = "0.0.0.0" }
if (-not $env:AUTH_PORT) { $env:AUTH_PORT = "8000" }
if (-not $env:STRATEGY_HOST) { $env:STRATEGY_HOST = "0.0.0.0" }
if (-not $env:STRATEGY_PORT) { $env:STRATEGY_PORT = "8002" }

# Check for required API keys
if (-not $env:EXCHANGE_API_KEY) {
    Write-Host "EXCHANGE_API_KEY environment variable is not set. Please set it before starting the Trade service."
    exit 1
}

if (-not $env:EXCHANGE_API_SECRET) {
    Write-Host "EXCHANGE_API_SECRET environment variable is not set. Please set it before starting the Trade service."
    exit 1
}

Write-Host "Starting Trade Service on $($env:TRADE_HOST):$($env:TRADE_PORT)"

# Check if database exists and is accessible
if ($env:TRADE_DB_URL -like "sqlite*") {
    $DB_PATH = $env:TRADE_DB_URL -replace "sqlite:///", ""
    if (-not (Test-Path $DB_PATH)) {
        Write-Host "Database file not found. Running migrations..."
        Push-Location trade
        python -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"
        Pop-Location
    }
}

# Check if Auth service is running
Write-Host "Checking Auth service connection..."
try {
    $response = Invoke-WebRequest -Uri "http://$($env:AUTH_HOST):$($env:AUTH_PORT)/health" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($response.StatusCode -ne 200) {
        Write-Host "Auth service is not running. Please start Auth service first."
        exit 1
    }
    Write-Host "Auth service connection successful."
} catch {
    Write-Host "Auth service is not running. Please start Auth service first."
    exit 1
}

# Check if Strategy service is running
Write-Host "Checking Strategy service connection..."
try {
    $response = Invoke-WebRequest -Uri "http://$($env:STRATEGY_HOST):$($env:STRATEGY_PORT)/health" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($response.StatusCode -ne 200) {
        Write-Host "Strategy service is not running. Please start Strategy service first."
        exit 1
    }
    Write-Host "Strategy service connection successful."
} catch {
    Write-Host "Strategy service is not running. Please start Strategy service first."
    exit 1
}

# Check if the service is already running
$PID_FILE = "$env:TEMP\cryptobot_trade.pid"
if (Test-Path $PID_FILE) {
    $PID = Get-Content $PID_FILE
    try {
        $process = Get-Process -Id $PID -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Trade service is already running with PID $PID"
            exit 0
        } else {
            Write-Host "Removing stale PID file"
            Remove-Item $PID_FILE
        }
    } catch {
        Write-Host "Removing stale PID file"
        Remove-Item $PID_FILE
    }
}

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# Start the service
Push-Location trade
Write-Host "Starting Trade service..."
$process = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--host", $env:TRADE_HOST, "--port", $env:TRADE_PORT, "--workers", $env:TRADE_WORKERS, "--log-level", $env:TRADE_LOG_LEVEL -RedirectStandardOutput "..\logs\trade_service.log" -RedirectStandardError "..\logs\trade_service_error.log" -NoNewWindow -PassThru
$process.Id | Out-File -FilePath $PID_FILE
Write-Host "Trade service started with PID $($process.Id)"
Pop-Location

# Wait for service to be ready
Write-Host "Waiting for Trade service to be ready..."
$MAX_RETRIES = 30
$RETRY_COUNT = 0
while ($RETRY_COUNT -lt $MAX_RETRIES) {
    try {
        $response = Invoke-WebRequest -Uri "http://$($env:TRADE_HOST):$($env:TRADE_PORT)/health" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "Trade service is ready!"
            break
        }
    } catch {
        # Continue if service is not ready
    }
    $RETRY_COUNT++
    Write-Host "Waiting for Trade service to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
    Start-Sleep -Seconds 1
}

if ($RETRY_COUNT -eq $MAX_RETRIES) {
    Write-Host "Trade service failed to start within the expected time"
    exit 1
}

Write-Host "Trade service started successfully"