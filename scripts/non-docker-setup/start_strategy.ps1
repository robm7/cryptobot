# Strategy Service Startup Script for Windows

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
if (-not $env:STRATEGY_HOST) { $env:STRATEGY_HOST = "0.0.0.0" }
if (-not $env:STRATEGY_PORT) { $env:STRATEGY_PORT = "8002" }
if (-not $env:STRATEGY_WORKERS) { $env:STRATEGY_WORKERS = "2" }
if (-not $env:STRATEGY_LOG_LEVEL) { $env:STRATEGY_LOG_LEVEL = "info" }
if (-not $env:STRATEGY_DB_URL) { $env:STRATEGY_DB_URL = "sqlite:///./strategy.db" }
if (-not $env:AUTH_HOST) { $env:AUTH_HOST = "0.0.0.0" }
if (-not $env:AUTH_PORT) { $env:AUTH_PORT = "8000" }
if (-not $env:DATA_HOST) { $env:DATA_HOST = "0.0.0.0" }
if (-not $env:DATA_PORT) { $env:DATA_PORT = "8001" }

Write-Host "Starting Strategy Service on $($env:STRATEGY_HOST):$($env:STRATEGY_PORT)"

# Check if database exists and is accessible
if ($env:STRATEGY_DB_URL -like "sqlite*") {
    $DB_PATH = $env:STRATEGY_DB_URL -replace "sqlite:///", ""
    if (-not (Test-Path $DB_PATH)) {
        Write-Host "Database file not found. Running migrations..."
        Push-Location strategy
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

# Check if the service is already running
$PID_FILE = "$env:TEMP\cryptobot_strategy.pid"
if (Test-Path $PID_FILE) {
    $PID = Get-Content $PID_FILE
    try {
        $process = Get-Process -Id $PID -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Strategy service is already running with PID $PID"
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
Push-Location strategy
Write-Host "Starting Strategy service..."
$process = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--host", $env:STRATEGY_HOST, "--port", $env:STRATEGY_PORT, "--workers", $env:STRATEGY_WORKERS, "--log-level", $env:STRATEGY_LOG_LEVEL -RedirectStandardOutput "..\logs\strategy_service.log" -RedirectStandardError "..\logs\strategy_service_error.log" -NoNewWindow -PassThru
$process.Id | Out-File -FilePath $PID_FILE
Write-Host "Strategy service started with PID $($process.Id)"
Pop-Location

# Wait for service to be ready
Write-Host "Waiting for Strategy service to be ready..."
$MAX_RETRIES = 30
$RETRY_COUNT = 0
while ($RETRY_COUNT -lt $MAX_RETRIES) {
    try {
        $response = Invoke-WebRequest -Uri "http://$($env:STRATEGY_HOST):$($env:STRATEGY_PORT)/health" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "Strategy service is ready!"
            break
        }
    } catch {
        # Continue if service is not ready
    }
    $RETRY_COUNT++
    Write-Host "Waiting for Strategy service to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
    Start-Sleep -Seconds 1
}

if ($RETRY_COUNT -eq $MAX_RETRIES) {
    Write-Host "Strategy service failed to start within the expected time"
    exit 1
}

Write-Host "Strategy service started successfully"