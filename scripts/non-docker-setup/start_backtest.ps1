# Backtest Service Startup Script for Windows

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
if (-not $env:BACKTEST_HOST) { $env:BACKTEST_HOST = "0.0.0.0" }
if (-not $env:BACKTEST_PORT) { $env:BACKTEST_PORT = "8003" }
if (-not $env:BACKTEST_WORKERS) { $env:BACKTEST_WORKERS = "2" }
if (-not $env:BACKTEST_LOG_LEVEL) { $env:BACKTEST_LOG_LEVEL = "info" }
if (-not $env:BACKTEST_DB_URL) { $env:BACKTEST_DB_URL = "sqlite:///./backtest.db" }
if (-not $env:AUTH_HOST) { $env:AUTH_HOST = "0.0.0.0" }
if (-not $env:AUTH_PORT) { $env:AUTH_PORT = "8000" }
if (-not $env:DATA_HOST) { $env:DATA_HOST = "0.0.0.0" }
if (-not $env:DATA_PORT) { $env:DATA_PORT = "8001" }
if (-not $env:STRATEGY_HOST) { $env:STRATEGY_HOST = "0.0.0.0" }
if (-not $env:STRATEGY_PORT) { $env:STRATEGY_PORT = "8002" }

Write-Host "Starting Backtest Service on $($env:BACKTEST_HOST):$($env:BACKTEST_PORT)"

# Check if database exists and is accessible
if ($env:BACKTEST_DB_URL -like "sqlite*") {
    $DB_PATH = $env:BACKTEST_DB_URL -replace "sqlite:///", ""
    if (-not (Test-Path $DB_PATH)) {
        Write-Host "Database file not found. Running migrations..."
        Push-Location backtest
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

# Check if Data service is running
Write-Host "Checking Data service connection..."
try {
    $response = Invoke-WebRequest -Uri "http://$($env:DATA_HOST):$($env:DATA_PORT)/health" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($response.StatusCode -ne 200) {
        Write-Host "Data service is not running. Please start Data service first."
        exit 1
    }
    Write-Host "Data service connection successful."
} catch {
    Write-Host "Data service is not running. Please start Data service first."
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
$PID_FILE = "$env:TEMP\cryptobot_backtest.pid"
if (Test-Path $PID_FILE) {
    $PID = Get-Content $PID_FILE
    try {
        $process = Get-Process -Id $PID -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Backtest service is already running with PID $PID"
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
Push-Location backtest
Write-Host "Starting Backtest service..."
$process = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--host", $env:BACKTEST_HOST, "--port", $env:BACKTEST_PORT, "--workers", $env:BACKTEST_WORKERS, "--log-level", $env:BACKTEST_LOG_LEVEL -RedirectStandardOutput "..\logs\backtest_service.log" -RedirectStandardError "..\logs\backtest_service_error.log" -NoNewWindow -PassThru
$process.Id | Out-File -FilePath $PID_FILE
Write-Host "Backtest service started with PID $($process.Id)"
Pop-Location

# Wait for service to be ready
Write-Host "Waiting for Backtest service to be ready..."
$MAX_RETRIES = 30
$RETRY_COUNT = 0
while ($RETRY_COUNT -lt $MAX_RETRIES) {
    try {
        $response = Invoke-WebRequest -Uri "http://$($env:BACKTEST_HOST):$($env:BACKTEST_PORT)/health" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "Backtest service is ready!"
            break
        }
    } catch {
        # Continue if service is not ready
    }
    $RETRY_COUNT++
    Write-Host "Waiting for Backtest service to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
    Start-Sleep -Seconds 1
}

if ($RETRY_COUNT -eq $MAX_RETRIES) {
    Write-Host "Backtest service failed to start within the expected time"
    exit 1
}

Write-Host "Backtest service started successfully"