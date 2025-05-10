# Auth Service Startup Script for Windows

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
if (-not $env:AUTH_HOST) { $env:AUTH_HOST = "0.0.0.0" }
if (-not $env:AUTH_PORT) { $env:AUTH_PORT = "8000" }
if (-not $env:AUTH_WORKERS) { $env:AUTH_WORKERS = "4" }
if (-not $env:AUTH_LOG_LEVEL) { $env:AUTH_LOG_LEVEL = "info" }
if (-not $env:AUTH_DB_URL) { $env:AUTH_DB_URL = "sqlite:///./auth.db" }

Write-Host "Starting Auth Service on $($env:AUTH_HOST):$($env:AUTH_PORT)"

# Check if database exists and is accessible
if ($env:AUTH_DB_URL -like "sqlite*") {
    $DB_PATH = $env:AUTH_DB_URL -replace "sqlite:///", ""
    if (-not (Test-Path $DB_PATH)) {
        Write-Host "Database file not found. Running migrations..."
        Push-Location auth
        python -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"
        Pop-Location
    }
}

# Check if the service is already running
$PID_FILE = "$env:TEMP\cryptobot_auth.pid"
if (Test-Path $PID_FILE) {
    $PID = Get-Content $PID_FILE
    try {
        $process = Get-Process -Id $PID -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Auth service is already running with PID $PID"
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
Push-Location auth
Write-Host "Starting Auth service..."
$process = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--host", $env:AUTH_HOST, "--port", $env:AUTH_PORT, "--workers", $env:AUTH_WORKERS, "--log-level", $env:AUTH_LOG_LEVEL -RedirectStandardOutput "..\logs\auth_service.log" -RedirectStandardError "..\logs\auth_service_error.log" -NoNewWindow -PassThru
$process.Id | Out-File -FilePath $PID_FILE
Write-Host "Auth service started with PID $($process.Id)"
Pop-Location

# Wait for service to be ready
Write-Host "Waiting for Auth service to be ready..."
$MAX_RETRIES = 30
$RETRY_COUNT = 0
while ($RETRY_COUNT -lt $MAX_RETRIES) {
    try {
        $response = Invoke-WebRequest -Uri "http://$($env:AUTH_HOST):$($env:AUTH_PORT)/health" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "Auth service is ready!"
            break
        }
    } catch {
        # Continue if service is not ready
    }
    $RETRY_COUNT++
    Write-Host "Waiting for Auth service to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
    Start-Sleep -Seconds 1
}

if ($RETRY_COUNT -eq $MAX_RETRIES) {
    Write-Host "Auth service failed to start within the expected time"
    exit 1
}

Write-Host "Auth service started successfully"