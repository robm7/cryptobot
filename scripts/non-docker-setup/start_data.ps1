# Data Service Startup Script for Windows

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
if (-not $env:DATA_HOST) { $env:DATA_HOST = "0.0.0.0" }
if (-not $env:DATA_PORT) { $env:DATA_PORT = "8001" }
if (-not $env:DATA_WORKERS) { $env:DATA_WORKERS = "2" }
if (-not $env:DATA_LOG_LEVEL) { $env:DATA_LOG_LEVEL = "info" }
if (-not $env:REDIS_HOST) { $env:REDIS_HOST = "localhost" }
if (-not $env:REDIS_PORT) { $env:REDIS_PORT = "6379" }
if (-not $env:REDIS_DB) { $env:REDIS_DB = "0" }
if (-not $env:AUTH_HOST) { $env:AUTH_HOST = "0.0.0.0" }
if (-not $env:AUTH_PORT) { $env:AUTH_PORT = "8000" }

Write-Host "Starting Data Service on $($env:DATA_HOST):$($env:DATA_PORT)"

# Check if Redis is running
Write-Host "Checking Redis connection..."
try {
    $redisCheck = Invoke-Expression "redis-cli -h $($env:REDIS_HOST) -p $($env:REDIS_PORT) ping"
    if ($redisCheck -ne "PONG") {
        Write-Host "Redis is not running. Please start Redis first."
        exit 1
    }
    Write-Host "Redis connection successful."
} catch {
    Write-Host "Redis is not running or redis-cli is not in PATH. Please start Redis first."
    exit 1
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

# Check if the service is already running
$PID_FILE = "$env:TEMP\cryptobot_data.pid"
if (Test-Path $PID_FILE) {
    $PID = Get-Content $PID_FILE
    try {
        $process = Get-Process -Id $PID -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Data service is already running with PID $PID"
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
Push-Location data
Write-Host "Starting Data service..."
$process = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--host", $env:DATA_HOST, "--port", $env:DATA_PORT, "--workers", $env:DATA_WORKERS, "--log-level", $env:DATA_LOG_LEVEL -RedirectStandardOutput "..\logs\data_service.log" -RedirectStandardError "..\logs\data_service_error.log" -NoNewWindow -PassThru
$process.Id | Out-File -FilePath $PID_FILE
Write-Host "Data service started with PID $($process.Id)"
Pop-Location

# Wait for service to be ready
Write-Host "Waiting for Data service to be ready..."
$MAX_RETRIES = 30
$RETRY_COUNT = 0
while ($RETRY_COUNT -lt $MAX_RETRIES) {
    try {
        $response = Invoke-WebRequest -Uri "http://$($env:DATA_HOST):$($env:DATA_PORT)/health" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "Data service is ready!"
            break
        }
    } catch {
        # Continue if service is not ready
    }
    $RETRY_COUNT++
    Write-Host "Waiting for Data service to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
    Start-Sleep -Seconds 1
}

if ($RETRY_COUNT -eq $MAX_RETRIES) {
    Write-Host "Data service failed to start within the expected time"
    exit 1
}

Write-Host "Data service started successfully"