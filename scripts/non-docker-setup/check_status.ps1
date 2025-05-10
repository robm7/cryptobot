# Service Status Monitoring Script for Windows

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

# Function to check if a service is running
function Check-Service {
    param (
        [string]$ServiceName,
        [string]$Host,
        [string]$Port,
        [string]$PidFile
    )
    
    Write-Host "Checking $ServiceName service..." -ForegroundColor Blue
    
    # Check if PID file exists
    if (Test-Path $PidFile) {
        $PID = Get-Content $PidFile
        try {
            $process = Get-Process -Id $PID -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "  ✓ Process is running with PID $PID" -ForegroundColor Green
                
                # Check if service endpoint is responding
                try {
                    $response = Invoke-WebRequest -Uri "http://$Host`:$Port/health" -UseBasicParsing -ErrorAction SilentlyContinue
                    if ($response.StatusCode -eq 200) {
                        Write-Host "  ✓ Service endpoint is responding at http://$Host`:$Port" -ForegroundColor Green
                        
                        # Get additional service information if available
                        try {
                            $info = Invoke-WebRequest -Uri "http://$Host`:$Port/info" -UseBasicParsing -ErrorAction SilentlyContinue
                            if ($info.StatusCode -eq 200) {
                                Write-Host "  ℹ Service information:" -ForegroundColor Blue
                                $info.Content | ForEach-Object { Write-Host "    $_" }
                            }
                        } catch {
                            # Info endpoint might not be available
                        }
                        
                        # Get service metrics if available
                        try {
                            $metrics = Invoke-WebRequest -Uri "http://$Host`:$Port/metrics" -UseBasicParsing -ErrorAction SilentlyContinue
                            if ($metrics.StatusCode -eq 200) {
                                Write-Host "  ℹ Service metrics:" -ForegroundColor Blue
                                $metrics.Content -split "`n" | Select-Object -First 5 | ForEach-Object { Write-Host "    $_" }
                                Write-Host "    ..."
                            }
                        } catch {
                            # Metrics endpoint might not be available
                        }
                        
                        return $true
                    } else {
                        Write-Host "  ✗ Process is running but service endpoint is not responding" -ForegroundColor Red
                        return $false
                    }
                } catch {
                    Write-Host "  ✗ Process is running but service endpoint is not responding" -ForegroundColor Red
                    return $false
                }
            } else {
                Write-Host "  ✗ Process with PID $PID is not running" -ForegroundColor Red
                Write-Host "  ! Removing stale PID file" -ForegroundColor Yellow
                Remove-Item $PidFile
                return $false
            }
        } catch {
            Write-Host "  ✗ Process with PID $PID is not running" -ForegroundColor Red
            Write-Host "  ! Removing stale PID file" -ForegroundColor Yellow
            Remove-Item $PidFile
            return $false
        }
    } else {
        Write-Host "  ✗ Service is not running (no PID file)" -ForegroundColor Red
        return $false
    }
}

# Function to check service logs
function Check-Logs {
    param (
        [string]$ServiceName,
        [string]$LogFile
    )
    
    Write-Host "Checking $ServiceName logs..." -ForegroundColor Blue
    
    if (Test-Path $LogFile) {
        Write-Host "  ✓ Log file exists: $LogFile" -ForegroundColor Green
        
        # Check for errors in logs
        $errorLines = Select-String -Path $LogFile -Pattern "error" -CaseSensitive:$false
        $errorCount = $errorLines.Count
        
        if ($errorCount -gt 0) {
            Write-Host "  ! Found $errorCount error(s) in logs" -ForegroundColor Yellow
            Write-Host "  ! Last 3 errors:" -ForegroundColor Yellow
            $errorLines | Select-Object -Last 3 | ForEach-Object { Write-Host "    $_" }
        } else {
            Write-Host "  ✓ No errors found in logs" -ForegroundColor Green
        }
        
        # Show last few log entries
        Write-Host "  ℹ Last 3 log entries:" -ForegroundColor Blue
        Get-Content $LogFile -Tail 3 | ForEach-Object { Write-Host "    $_" }
    } else {
        Write-Host "  ! Log file not found: $LogFile" -ForegroundColor Yellow
    }
}

# Display banner
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  CryptoBot Services - Status Monitor" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running with administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "Warning: This script is running with administrator privileges." -ForegroundColor Yellow
    Write-Host ""
}

# Check all services
Write-Host "Checking service status..." -ForegroundColor Cyan
Write-Host ""

# Check Auth service
$authStatus = Check-Service -ServiceName "Auth" -Host $env:AUTH_HOST -Port $env:AUTH_PORT -PidFile "$env:TEMP\cryptobot_auth.pid"
Check-Logs -ServiceName "Auth" -LogFile ".\logs\auth_service.log"
Write-Host ""

# Check Data service
$dataStatus = Check-Service -ServiceName "Data" -Host $env:DATA_HOST -Port $env:DATA_PORT -PidFile "$env:TEMP\cryptobot_data.pid"
Check-Logs -ServiceName "Data" -LogFile ".\logs\data_service.log"
Write-Host ""

# Check Strategy service
$strategyStatus = Check-Service -ServiceName "Strategy" -Host $env:STRATEGY_HOST -Port $env:STRATEGY_PORT -PidFile "$env:TEMP\cryptobot_strategy.pid"
Check-Logs -ServiceName "Strategy" -LogFile ".\logs\strategy_service.log"
Write-Host ""

# Check Backtest service
$backtestStatus = Check-Service -ServiceName "Backtest" -Host $env:BACKTEST_HOST -Port $env:BACKTEST_PORT -PidFile "$env:TEMP\cryptobot_backtest.pid"
Check-Logs -ServiceName "Backtest" -LogFile ".\logs\backtest_service.log"
Write-Host ""

# Check Trade service
$tradeStatus = Check-Service -ServiceName "Trade" -Host $env:TRADE_HOST -Port $env:TRADE_PORT -PidFile "$env:TEMP\cryptobot_trade.pid"
Check-Logs -ServiceName "Trade" -LogFile ".\logs\trade_service.log"
Write-Host ""

# Display summary
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Service Status Summary" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

if ($authStatus) {
    Write-Host "Auth Service:     " -NoNewline
    Write-Host "Running" -ForegroundColor Green
} else {
    Write-Host "Auth Service:     " -NoNewline
    Write-Host "Not Running" -ForegroundColor Red
}

if ($dataStatus) {
    Write-Host "Data Service:     " -NoNewline
    Write-Host "Running" -ForegroundColor Green
} else {
    Write-Host "Data Service:     " -NoNewline
    Write-Host "Not Running" -ForegroundColor Red
}

if ($strategyStatus) {
    Write-Host "Strategy Service: " -NoNewline
    Write-Host "Running" -ForegroundColor Green
} else {
    Write-Host "Strategy Service: " -NoNewline
    Write-Host "Not Running" -ForegroundColor Red
}

if ($backtestStatus) {
    Write-Host "Backtest Service: " -NoNewline
    Write-Host "Running" -ForegroundColor Green
} else {
    Write-Host "Backtest Service: " -NoNewline
    Write-Host "Not Running" -ForegroundColor Red
}

if ($tradeStatus) {
    Write-Host "Trade Service:    " -NoNewline
    Write-Host "Running" -ForegroundColor Green
} else {
    Write-Host "Trade Service:    " -NoNewline
    Write-Host "Not Running" -ForegroundColor Red
}

Write-Host ""
Write-Host "To start all services, run: .\scripts\non-docker-setup\start_all.ps1"
Write-Host "To stop all services, run: .\scripts\non-docker-setup\orchestrate_services.ps1 stop all"
Write-Host ""