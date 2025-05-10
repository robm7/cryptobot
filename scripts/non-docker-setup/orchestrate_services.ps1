# Service Orchestration Script for Windows

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

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# Function to check if a service is running
function Check-Service {
    param (
        [string]$ServiceName,
        [string]$Host,
        [string]$Port
    )
    
    Write-Host "Checking if $ServiceName is running at $Host`:$Port..."
    try {
        $response = Invoke-WebRequest -Uri "http://$Host`:$Port/health" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "$ServiceName is running."
            return $true
        } else {
            Write-Host "$ServiceName is not running."
            return $false
        }
    } catch {
        Write-Host "$ServiceName is not running."
        return $false
    }
}

# Function to start a service and wait for it to be ready
function Start-CryptoService {
    param (
        [string]$ServiceName,
        [string]$ScriptPath,
        [string]$Host,
        [string]$Port
    )
    
    Write-Host "Starting $ServiceName..."
    
    # Check if service is already running
    if (Check-Service -ServiceName $ServiceName -Host $Host -Port $Port) {
        Write-Host "$ServiceName is already running."
        return $true
    }
    
    # Start the service
    & $ScriptPath
    
    # Check if service started successfully
    if (Check-Service -ServiceName $ServiceName -Host $Host -Port $Port) {
        Write-Host "$ServiceName started successfully."
        return $true
    } else {
        Write-Host "Failed to start $ServiceName."
        return $false
    }
}

# Function to stop a service
function Stop-CryptoService {
    param (
        [string]$ServiceName,
        [string]$PidFile
    )
    
    if (Test-Path $PidFile) {
        $PID = Get-Content $PidFile
        try {
            $process = Get-Process -Id $PID -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "Stopping $ServiceName with PID $PID..."
                Stop-Process -Id $PID -Force
                Remove-Item $PidFile
                Write-Host "$ServiceName stopped."
            } else {
                Write-Host "$ServiceName is not running."
                Remove-Item $PidFile
            }
        } catch {
            Write-Host "$ServiceName is not running."
            Remove-Item $PidFile
        }
    } else {
        Write-Host "$ServiceName is not running."
    }
}

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

# Command line arguments
$Action = if ($args.Length -ge 1) { $args[0] } else { "start" }
$Service = if ($args.Length -ge 2) { $args[1] } else { "all" }

switch ($Action) {
    "start" {
        switch ($Service) {
            "all" {
                Write-Host "Starting all services in the correct order..."
                
                # Start Auth service first
                $result = Start-CryptoService -ServiceName "Auth" -ScriptPath ".\scripts\non-docker-setup\start_auth.ps1" -Host $env:AUTH_HOST -Port $env:AUTH_PORT
                if (-not $result) { exit 1 }
                
                # Start Data service next
                $result = Start-CryptoService -ServiceName "Data" -ScriptPath ".\scripts\non-docker-setup\start_data.ps1" -Host $env:DATA_HOST -Port $env:DATA_PORT
                if (-not $result) { exit 1 }
                
                # Start Strategy service
                $result = Start-CryptoService -ServiceName "Strategy" -ScriptPath ".\scripts\non-docker-setup\start_strategy.ps1" -Host $env:STRATEGY_HOST -Port $env:STRATEGY_PORT
                if (-not $result) { exit 1 }
                
                # Start Backtest service
                $result = Start-CryptoService -ServiceName "Backtest" -ScriptPath ".\scripts\non-docker-setup\start_backtest.ps1" -Host $env:BACKTEST_HOST -Port $env:BACKTEST_PORT
                if (-not $result) { exit 1 }
                
                # Start Trade service
                $result = Start-CryptoService -ServiceName "Trade" -ScriptPath ".\scripts\non-docker-setup\start_trade.ps1" -Host $env:TRADE_HOST -Port $env:TRADE_PORT
                if (-not $result) { exit 1 }
                
                Write-Host "All services started successfully."
            }
            "auth" {
                Start-CryptoService -ServiceName "Auth" -ScriptPath ".\scripts\non-docker-setup\start_auth.ps1" -Host $env:AUTH_HOST -Port $env:AUTH_PORT
            }
            "data" {
                # Check if Auth service is running
                if (-not (Check-Service -ServiceName "Auth" -Host $env:AUTH_HOST -Port $env:AUTH_PORT)) {
                    Write-Host "Auth service must be running before starting Data service."
                    exit 1
                }
                
                Start-CryptoService -ServiceName "Data" -ScriptPath ".\scripts\non-docker-setup\start_data.ps1" -Host $env:DATA_HOST -Port $env:DATA_PORT
            }
            "strategy" {
                # Check if Auth service is running
                if (-not (Check-Service -ServiceName "Auth" -Host $env:AUTH_HOST -Port $env:AUTH_PORT)) {
                    Write-Host "Auth service must be running before starting Strategy service."
                    exit 1
                }
                
                # Check if Data service is running
                if (-not (Check-Service -ServiceName "Data" -Host $env:DATA_HOST -Port $env:DATA_PORT)) {
                    Write-Host "Data service must be running before starting Strategy service."
                    exit 1
                }
                
                Start-CryptoService -ServiceName "Strategy" -ScriptPath ".\scripts\non-docker-setup\start_strategy.ps1" -Host $env:STRATEGY_HOST -Port $env:STRATEGY_PORT
            }
            "backtest" {
                # Check if Auth service is running
                if (-not (Check-Service -ServiceName "Auth" -Host $env:AUTH_HOST -Port $env:AUTH_PORT)) {
                    Write-Host "Auth service must be running before starting Backtest service."
                    exit 1
                }
                
                # Check if Data service is running
                if (-not (Check-Service -ServiceName "Data" -Host $env:DATA_HOST -Port $env:DATA_PORT)) {
                    Write-Host "Data service must be running before starting Backtest service."
                    exit 1
                }
                
                # Check if Strategy service is running
                if (-not (Check-Service -ServiceName "Strategy" -Host $env:STRATEGY_HOST -Port $env:STRATEGY_PORT)) {
                    Write-Host "Strategy service must be running before starting Backtest service."
                    exit 1
                }
                
                Start-CryptoService -ServiceName "Backtest" -ScriptPath ".\scripts\non-docker-setup\start_backtest.ps1" -Host $env:BACKTEST_HOST -Port $env:BACKTEST_PORT
            }
            "trade" {
                # Check if Auth service is running
                if (-not (Check-Service -ServiceName "Auth" -Host $env:AUTH_HOST -Port $env:AUTH_PORT)) {
                    Write-Host "Auth service must be running before starting Trade service."
                    exit 1
                }
                
                # Check if Strategy service is running
                if (-not (Check-Service -ServiceName "Strategy" -Host $env:STRATEGY_HOST -Port $env:STRATEGY_PORT)) {
                    Write-Host "Strategy service must be running before starting Trade service."
                    exit 1
                }
                
                Start-CryptoService -ServiceName "Trade" -ScriptPath ".\scripts\non-docker-setup\start_trade.ps1" -Host $env:TRADE_HOST -Port $env:TRADE_PORT
            }
            default {
                Write-Host "Unknown service: $Service"
                Write-Host "Available services: all, auth, data, strategy, backtest, trade"
                exit 1
            }
        }
    }
    "stop" {
        switch ($Service) {
            "all" {
                Write-Host "Stopping all services in the reverse order..."
                
                # Stop Trade service first
                Stop-CryptoService -ServiceName "Trade" -PidFile "$env:TEMP\cryptobot_trade.pid"
                
                # Stop Backtest service
                Stop-CryptoService -ServiceName "Backtest" -PidFile "$env:TEMP\cryptobot_backtest.pid"
                
                # Stop Strategy service
                Stop-CryptoService -ServiceName "Strategy" -PidFile "$env:TEMP\cryptobot_strategy.pid"
                
                # Stop Data service
                Stop-CryptoService -ServiceName "Data" -PidFile "$env:TEMP\cryptobot_data.pid"
                
                # Stop Auth service last
                Stop-CryptoService -ServiceName "Auth" -PidFile "$env:TEMP\cryptobot_auth.pid"
                
                Write-Host "All services stopped."
            }
            "auth" {
                Stop-CryptoService -ServiceName "Auth" -PidFile "$env:TEMP\cryptobot_auth.pid"
            }
            "data" {
                Stop-CryptoService -ServiceName "Data" -PidFile "$env:TEMP\cryptobot_data.pid"
            }
            "strategy" {
                Stop-CryptoService -ServiceName "Strategy" -PidFile "$env:TEMP\cryptobot_strategy.pid"
            }
            "backtest" {
                Stop-CryptoService -ServiceName "Backtest" -PidFile "$env:TEMP\cryptobot_backtest.pid"
            }
            "trade" {
                Stop-CryptoService -ServiceName "Trade" -PidFile "$env:TEMP\cryptobot_trade.pid"
            }
            default {
                Write-Host "Unknown service: $Service"
                Write-Host "Available services: all, auth, data, strategy, backtest, trade"
                exit 1
            }
        }
    }
    "restart" {
        switch ($Service) {
            "all" {
                Write-Host "Restarting all services..."
                & $PSCommandPath stop all
                Start-Sleep -Seconds 2
                & $PSCommandPath start all
            }
            default {
                Write-Host "Restarting $Service service..."
                & $PSCommandPath stop $Service
                Start-Sleep -Seconds 2
                & $PSCommandPath start $Service
            }
        }
    }
    "status" {
        Write-Host "Checking status of all services..."
        
        Check-Service -ServiceName "Auth" -Host $env:AUTH_HOST -Port $env:AUTH_PORT
        Check-Service -ServiceName "Data" -Host $env:DATA_HOST -Port $env:DATA_PORT
        Check-Service -ServiceName "Strategy" -Host $env:STRATEGY_HOST -Port $env:STRATEGY_PORT
        Check-Service -ServiceName "Backtest" -Host $env:BACKTEST_HOST -Port $env:BACKTEST_PORT
        Check-Service -ServiceName "Trade" -Host $env:TRADE_HOST -Port $env:TRADE_PORT
    }
    default {
        Write-Host "Unknown action: $Action"
        Write-Host "Available actions: start, stop, restart, status"
        Write-Host "Usage: .\orchestrate_services.ps1 [action] [service]"
        Write-Host "  action: start, stop, restart, status"
        Write-Host "  service: all, auth, data, strategy, backtest, trade"
        exit 1
    }
}

exit 0