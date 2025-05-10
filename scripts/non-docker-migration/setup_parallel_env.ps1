# setup_parallel_env.ps1
# Script to set up parallel Docker and non-Docker environments for Cryptobot on Windows
# Part of Phase 11: Parallel Operation Strategy

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "This script requires Administrator privileges. Please run as Administrator." -ForegroundColor Red
    exit 1
}

Write-Host "=== Cryptobot Parallel Environment Setup ===" -ForegroundColor Cyan
Write-Host "This script will configure both Docker and non-Docker environments to run simultaneously." -ForegroundColor Cyan

# Define directories
$DOCKER_ENV_DIR = "C:\cryptobot\docker"
$NON_DOCKER_ENV_DIR = "C:\cryptobot\non-docker"
$SHARED_DATA_DIR = "C:\cryptobot\shared_data"
$LOG_DIR = "C:\cryptobot\logs"

# Create directories
Write-Host "Creating directory structure..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $DOCKER_ENV_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $NON_DOCKER_ENV_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $SHARED_DATA_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null
New-Item -ItemType Directory -Force -Path "$SHARED_DATA_DIR\database" | Out-Null
New-Item -ItemType Directory -Force -Path "$SHARED_DATA_DIR\historical_data" | Out-Null
New-Item -ItemType Directory -Force -Path "$SHARED_DATA_DIR\user_data" | Out-Null
New-Item -ItemType Directory -Force -Path "$SHARED_DATA_DIR\config" | Out-Null

# Configure Docker environment
Write-Host "Configuring Docker environment..." -ForegroundColor Green
# Create Docker Compose override file to use shared volumes
@"
version: '3'

services:
  postgres:
    volumes:
      - $($SHARED_DATA_DIR.Replace('\', '/'))/database:/var/lib/postgresql/data
    ports:
      - "5432:5432"
      
  redis:
    volumes:
      - $($SHARED_DATA_DIR.Replace('\', '/'))/redis:/data
    ports:
      - "6379:6379"
      
  auth:
    volumes:
      - $($SHARED_DATA_DIR.Replace('\', '/'))/config:/app/config
      - $($LOG_DIR.Replace('\', '/'))/:/app/logs
    ports:
      - "8000:8000"
      
  strategy:
    volumes:
      - $($SHARED_DATA_DIR.Replace('\', '/'))/config:/app/config
      - $($LOG_DIR.Replace('\', '/'))/:/app/logs
    ports:
      - "8001:8001"
      
  backtest:
    volumes:
      - $($SHARED_DATA_DIR.Replace('\', '/'))/historical_data:/app/data
      - $($SHARED_DATA_DIR.Replace('\', '/'))/config:/app/config
      - $($LOG_DIR.Replace('\', '/'))/:/app/logs
    ports:
      - "8002:8002"
      
  trade:
    volumes:
      - $($SHARED_DATA_DIR.Replace('\', '/'))/user_data:/app/user_data
      - $($SHARED_DATA_DIR.Replace('\', '/'))/config:/app/config
      - $($LOG_DIR.Replace('\', '/'))/:/app/logs
    ports:
      - "8003:8003"
      
  data:
    volumes:
      - $($SHARED_DATA_DIR.Replace('\', '/'))/historical_data:/app/data
      - $($SHARED_DATA_DIR.Replace('\', '/'))/config:/app/config
      - $($LOG_DIR.Replace('\', '/'))/:/app/logs
    ports:
      - "8004:8004"
"@ | Out-File -FilePath "$DOCKER_ENV_DIR\docker-compose.override.yml" -Encoding utf8

# Configure non-Docker environment
Write-Host "Configuring non-Docker environment..." -ForegroundColor Green
# Create configuration file for non-Docker services
@"
{
  "shared_data_dir": "$($SHARED_DATA_DIR.Replace('\', '\\'))",
  "log_dir": "$($LOG_DIR.Replace('\', '\\'))",
  "database": {
    "host": "localhost",
    "port": 5432,
    "user": "cryptobot",
    "password": "use_env_var_in_production",
    "database": "cryptobot"
  },
  "redis": {
    "host": "localhost",
    "port": 6379
  },
  "services": {
    "auth": {
      "host": "localhost",
      "port": 9000,
      "config_dir": "$($SHARED_DATA_DIR.Replace('\', '\\'))\\config",
      "log_dir": "$($LOG_DIR.Replace('\', '\\'))"
    },
    "strategy": {
      "host": "localhost",
      "port": 9001,
      "config_dir": "$($SHARED_DATA_DIR.Replace('\', '\\'))\\config",
      "log_dir": "$($LOG_DIR.Replace('\', '\\'))"
    },
    "backtest": {
      "host": "localhost",
      "port": 9002,
      "data_dir": "$($SHARED_DATA_DIR.Replace('\', '\\'))\\historical_data",
      "config_dir": "$($SHARED_DATA_DIR.Replace('\', '\\'))\\config",
      "log_dir": "$($LOG_DIR.Replace('\', '\\'))"
    },
    "trade": {
      "host": "localhost",
      "port": 9003,
      "user_data_dir": "$($SHARED_DATA_DIR.Replace('\', '\\'))\\user_data",
      "config_dir": "$($SHARED_DATA_DIR.Replace('\', '\\'))\\config",
      "log_dir": "$($LOG_DIR.Replace('\', '\\'))"
    },
    "data": {
      "host": "localhost",
      "port": 9004,
      "data_dir": "$($SHARED_DATA_DIR.Replace('\', '\\'))\\historical_data",
      "config_dir": "$($SHARED_DATA_DIR.Replace('\', '\\'))\\config",
      "log_dir": "$($LOG_DIR.Replace('\', '\\'))"
    }
  }
}
"@ | Out-File -FilePath "$NON_DOCKER_ENV_DIR\config.json" -Encoding utf8

# Configure networking
Write-Host "Configuring networking for parallel operation..." -ForegroundColor Green
# Add hosts file entries for service discovery
$hostsFile = "$env:windir\System32\drivers\etc\hosts"
$hostsContent = Get-Content $hostsFile
$newEntries = @"

# Cryptobot parallel environment service discovery
127.0.0.1 auth-docker auth-non-docker
127.0.0.1 strategy-docker strategy-non-docker
127.0.0.1 backtest-docker backtest-non-docker
127.0.0.1 trade-docker trade-non-docker
127.0.0.1 data-docker data-non-docker
"@

if (-not ($hostsContent -match "Cryptobot parallel environment")) {
    Add-Content -Path $hostsFile -Value $newEntries
    Write-Host "Added service discovery entries to hosts file." -ForegroundColor Green
} else {
    Write-Host "Service discovery entries already exist in hosts file." -ForegroundColor Yellow
}

# Create environment variables file
@"
# Environment variables for Cryptobot parallel environment

# Shared directories
$env:CRYPTOBOT_SHARED_DATA_DIR="$SHARED_DATA_DIR"
$env:CRYPTOBOT_LOG_DIR="$LOG_DIR"

# Database configuration
$env:CRYPTOBOT_DB_HOST="localhost"
$env:CRYPTOBOT_DB_PORT="5432"
$env:CRYPTOBOT_DB_USER="cryptobot"
$env:CRYPTOBOT_DB_PASSWORD="use_env_var_in_production"
$env:CRYPTOBOT_DB_NAME="cryptobot"

# Redis configuration
$env:CRYPTOBOT_REDIS_HOST="localhost"
$env:CRYPTOBOT_REDIS_PORT="6379"

# Docker service ports (8000-8004)
$env:CRYPTOBOT_DOCKER_AUTH_PORT="8000"
$env:CRYPTOBOT_DOCKER_STRATEGY_PORT="8001"
$env:CRYPTOBOT_DOCKER_BACKTEST_PORT="8002"
$env:CRYPTOBOT_DOCKER_TRADE_PORT="8003"
$env:CRYPTOBOT_DOCKER_DATA_PORT="8004"

# Non-Docker service ports (9000-9004)
$env:CRYPTOBOT_NON_DOCKER_AUTH_PORT="9000"
$env:CRYPTOBOT_NON_DOCKER_STRATEGY_PORT="9001"
$env:CRYPTOBOT_NON_DOCKER_BACKTEST_PORT="9002"
$env:CRYPTOBOT_NON_DOCKER_TRADE_PORT="9003"
$env:CRYPTOBOT_NON_DOCKER_DATA_PORT="9004"

# Parallel environment flag
$env:CRYPTOBOT_PARALLEL_ENV="true"
"@ | Out-File -FilePath "$SHARED_DATA_DIR\config\environment.ps1" -Encoding utf8

Write-Host "Creating service startup scripts..." -ForegroundColor Green
# Create startup script for non-Docker services
@"
# Start non-Docker Cryptobot services

. "$SHARED_DATA_DIR\config\environment.ps1"

Write-Host "Starting non-Docker Cryptobot services..." -ForegroundColor Cyan

# Start auth service
Set-Location "$NON_DOCKER_ENV_DIR\auth"
Start-Process -FilePath "python" -ArgumentList "main.py --port $env:CRYPTOBOT_NON_DOCKER_AUTH_PORT" -RedirectStandardOutput "$LOG_DIR\auth.log" -NoNewWindow
Write-Host "Auth service started on port $env:CRYPTOBOT_NON_DOCKER_AUTH_PORT" -ForegroundColor Green

# Start strategy service
Set-Location "$NON_DOCKER_ENV_DIR\strategy"
Start-Process -FilePath "python" -ArgumentList "main.py --port $env:CRYPTOBOT_NON_DOCKER_STRATEGY_PORT" -RedirectStandardOutput "$LOG_DIR\strategy.log" -NoNewWindow
Write-Host "Strategy service started on port $env:CRYPTOBOT_NON_DOCKER_STRATEGY_PORT" -ForegroundColor Green

# Start backtest service
Set-Location "$NON_DOCKER_ENV_DIR\backtest"
Start-Process -FilePath "python" -ArgumentList "main.py --port $env:CRYPTOBOT_NON_DOCKER_BACKTEST_PORT" -RedirectStandardOutput "$LOG_DIR\backtest.log" -NoNewWindow
Write-Host "Backtest service started on port $env:CRYPTOBOT_NON_DOCKER_BACKTEST_PORT" -ForegroundColor Green

# Start trade service
Set-Location "$NON_DOCKER_ENV_DIR\trade"
Start-Process -FilePath "python" -ArgumentList "main.py --port $env:CRYPTOBOT_NON_DOCKER_TRADE_PORT" -RedirectStandardOutput "$LOG_DIR\trade.log" -NoNewWindow
Write-Host "Trade service started on port $env:CRYPTOBOT_NON_DOCKER_TRADE_PORT" -ForegroundColor Green

# Start data service
Set-Location "$NON_DOCKER_ENV_DIR\data"
Start-Process -FilePath "python" -ArgumentList "main.py --port $env:CRYPTOBOT_NON_DOCKER_DATA_PORT" -RedirectStandardOutput "$LOG_DIR\data.log" -NoNewWindow
Write-Host "Data service started on port $env:CRYPTOBOT_NON_DOCKER_DATA_PORT" -ForegroundColor Green

Write-Host "All non-Docker services started." -ForegroundColor Cyan
"@ | Out-File -FilePath "$NON_DOCKER_ENV_DIR\start_services.ps1" -Encoding utf8

# Create stop script for non-Docker services
@"
# Stop non-Docker Cryptobot services

Write-Host "Stopping non-Docker Cryptobot services..." -ForegroundColor Cyan

# Function to kill process by port
function Stop-ProcessByPort {
    param (
        [int]`$Port
    )
    
    `$process = Get-NetTCPConnection -LocalPort `$Port -ErrorAction SilentlyContinue | 
               Select-Object -ExpandProperty OwningProcess | 
               Get-Process -ErrorAction SilentlyContinue
    
    if (`$process) {
        Write-Host "Stopping service on port `$Port (PID: `$(`$process.Id))" -ForegroundColor Green
        Stop-Process -Id `$process.Id -Force
    } else {
        Write-Host "No service found on port `$Port" -ForegroundColor Yellow
    }
}

# Load environment variables
. "$SHARED_DATA_DIR\config\environment.ps1"

# Stop all services
Stop-ProcessByPort -Port `$env:CRYPTOBOT_NON_DOCKER_AUTH_PORT
Stop-ProcessByPort -Port `$env:CRYPTOBOT_NON_DOCKER_STRATEGY_PORT
Stop-ProcessByPort -Port `$env:CRYPTOBOT_NON_DOCKER_BACKTEST_PORT
Stop-ProcessByPort -Port `$env:CRYPTOBOT_NON_DOCKER_TRADE_PORT
Stop-ProcessByPort -Port `$env:CRYPTOBOT_NON_DOCKER_DATA_PORT

Write-Host "All non-Docker services stopped." -ForegroundColor Cyan
"@ | Out-File -FilePath "$NON_DOCKER_ENV_DIR\stop_services.ps1" -Encoding utf8

Write-Host "=== Parallel Environment Setup Complete ===" -ForegroundColor Cyan
Write-Host "Docker environment: $DOCKER_ENV_DIR" -ForegroundColor White
Write-Host "Non-Docker environment: $NON_DOCKER_ENV_DIR" -ForegroundColor White
Write-Host "Shared data directory: $SHARED_DATA_DIR" -ForegroundColor White
Write-Host "Log directory: $LOG_DIR" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start Docker services: cd $DOCKER_ENV_DIR && docker-compose up -d" -ForegroundColor Yellow
Write-Host "2. Start non-Docker services: & '$NON_DOCKER_ENV_DIR\start_services.ps1'" -ForegroundColor Yellow
Write-Host "3. Set up data synchronization: & 'scripts\non-docker-migration\sync_data.ps1'" -ForegroundColor Yellow
Write-Host ""
Write-Host "For more information, see the migration documentation." -ForegroundColor Yellow