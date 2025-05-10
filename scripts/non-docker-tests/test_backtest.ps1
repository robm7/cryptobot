# Backtest Service Test Script (PowerShell)
# Tests backtest service functionality

# Set environment variables
$env:PYTHONPATH = (Get-Location).Path
$env:TEST_MODE = "true"

Write-Host "===== Backtest Service Test =====" -ForegroundColor Cyan
Write-Host "Starting backtest service tests..." -ForegroundColor Cyan

# Check if backtest service is running
Write-Host "Checking if backtest service is running..." -ForegroundColor Cyan
$backtestProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*backtest/main.py*" }
if ($backtestProcess) {
    Write-Host "Backtest service is running." -ForegroundColor Green
} else {
    Write-Host "Backtest service is not running. Starting backtest service..." -ForegroundColor Yellow
    # Start backtest service if not running
    & "$PSScriptRoot\..\non-docker-setup\start_backtest.ps1"
    Start-Sleep -Seconds 5  # Wait for service to start
}

# Run unit tests for backtest service
Write-Host "Running backtest service unit tests..." -ForegroundColor Cyan
python -m pytest tests/test_backtest.py -v

# Test backtest API endpoints
Write-Host "Testing backtest API endpoints..." -ForegroundColor Cyan
# Get auth token first
$loginBody = @{
    username = "test_user"
    password = "password123"
} | ConvertTo-Json

try {
    $authResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" -Method Post -ContentType "application/json" -Body $loginBody -ErrorAction Stop
    $token = $authResponse.access_token
    
    if (-not $token) {
        Write-Host "Failed to get access token." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to get access token: $_" -ForegroundColor Red
    exit 1
}

# Create a test strategy for backtesting
$strategyData = @{
    name = "Test Breakout Strategy"
    type = "breakout"
    parameters = @{
        breakout_period = 20
        atr_period = 14
        atr_multiplier = 2.0
        take_profit = 0.05
        stop_loss = 0.03
    }
    symbols = @("BTCUSDT")
    timeframe = "1h"
    status = "active"
} | ConvertTo-Json

try {
    $createResponse = Invoke-RestMethod -Uri "http://localhost:8000/strategy" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $strategyData -ErrorAction Stop
    $strategyId = $createResponse.id
    
    if (-not $strategyId) {
        Write-Host "Failed to create strategy for backtest." -ForegroundColor Red
        exit 1
    } else {
        Write-Host "Successfully created strategy with ID: $strategyId" -ForegroundColor Green
    }
} catch {
    Write-Host "Failed to create strategy for backtest: $_" -ForegroundColor Red
    exit 1
}

# Test backtest creation
Write-Host "Testing backtest creation..." -ForegroundColor Cyan
$backtestData = @{
    strategy_id = $strategyId
    start_date = "2025-01-01T00:00:00Z"
    end_date = "2025-01-31T23:59:59Z"
    initial_capital = 10000
    symbols = @("BTCUSDT")
    timeframe = "1h"
} | ConvertTo-Json

try {
    $backtestResponse = Invoke-RestMethod -Uri "http://localhost:8000/backtest" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $backtestData -ErrorAction Stop
    $backtestId = $backtestResponse.id
    
    if (-not $backtestId) {
        Write-Host "Failed to create backtest." -ForegroundColor Red
        exit 1
    } else {
        Write-Host "Successfully created backtest with ID: $backtestId" -ForegroundColor Green
    }
} catch {
    Write-Host "Failed to create backtest: $_" -ForegroundColor Red
    exit 1
}

# Test backtest status retrieval
Write-Host "Testing backtest status retrieval..." -ForegroundColor Cyan
# Wait for backtest to complete (or timeout after 30 seconds)
$maxAttempts = 30
$attempts = 0
$completed = $false

while ($attempts -lt $maxAttempts) {
    try {
        $statusResponse = Invoke-RestMethod -Uri "http://localhost:8000/backtest/$backtestId/status" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
        $status = $statusResponse.status
        
        if ($status -eq "completed") {
            $completed = $true
            Write-Host "Backtest completed successfully." -ForegroundColor Green
            break
        } elseif ($status -eq "failed") {
            Write-Host "Backtest failed." -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Backtest status: $status. Waiting..." -ForegroundColor Yellow
        $attempts++
        Start-Sleep -Seconds 1
    } catch {
        Write-Host "Error checking backtest status: $_" -ForegroundColor Red
        exit 1
    }
}

if (-not $completed) {
    Write-Host "Backtest did not complete within timeout period." -ForegroundColor Red
    exit 1
}

# Test backtest results retrieval
Write-Host "Testing backtest results retrieval..." -ForegroundColor Cyan
try {
    $resultsResponse = Invoke-RestMethod -Uri "http://localhost:8000/backtest/$backtestId/results" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($resultsResponse.total_return) {
        Write-Host "Successfully retrieved backtest results." -ForegroundColor Green
    } else {
        Write-Host "Failed to retrieve backtest results." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to retrieve backtest results: $_" -ForegroundColor Red
    exit 1
}

# Test backtest comparison
Write-Host "Testing backtest comparison..." -ForegroundColor Cyan
# Create another backtest with different parameters
$strategyData2 = @{
    name = "Test Breakout Strategy 2"
    type = "breakout"
    parameters = @{
        breakout_period = 30
        atr_period = 10
        atr_multiplier = 1.5
        take_profit = 0.06
        stop_loss = 0.02
    }
    symbols = @("BTCUSDT")
    timeframe = "1h"
    status = "active"
} | ConvertTo-Json

try {
    $createResponse2 = Invoke-RestMethod -Uri "http://localhost:8000/strategy" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $strategyData2 -ErrorAction Stop
    $strategyId2 = $createResponse2.id
    
    $backtestData2 = @{
        strategy_id = $strategyId2
        start_date = "2025-01-01T00:00:00Z"
        end_date = "2025-01-31T23:59:59Z"
        initial_capital = 10000
        symbols = @("BTCUSDT")
        timeframe = "1h"
    } | ConvertTo-Json
    
    $backtestResponse2 = Invoke-RestMethod -Uri "http://localhost:8000/backtest" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $backtestData2 -ErrorAction Stop
    $backtestId2 = $backtestResponse2.id
    
    # Wait for second backtest to complete
    $attempts = 0
    $completed = $false
    
    while ($attempts -lt $maxAttempts) {
        $statusResponse2 = Invoke-RestMethod -Uri "http://localhost:8000/backtest/$backtestId2/status" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
        $status = $statusResponse2.status
        
        if ($status -eq "completed") {
            $completed = $true
            Write-Host "Second backtest completed successfully." -ForegroundColor Green
            break
        } elseif ($status -eq "failed") {
            Write-Host "Second backtest failed." -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Second backtest status: $status. Waiting..." -ForegroundColor Yellow
        $attempts++
        Start-Sleep -Seconds 1
    }
    
    if (-not $completed) {
        Write-Host "Second backtest did not complete within timeout period." -ForegroundColor Red
        exit 1
    }
    
    # Compare backtests
    $compareData = @{
        backtest_ids = @($backtestId, $backtestId2)
    } | ConvertTo-Json
    
    $compareResponse = Invoke-RestMethod -Uri "http://localhost:8000/backtest/compare" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $compareData -ErrorAction Stop
    
    if ($compareResponse.comparison) {
        Write-Host "Successfully compared backtests." -ForegroundColor Green
    } else {
        Write-Host "Failed to compare backtests." -ForegroundColor Red
        exit 1
    }
    
    # Clean up
    Write-Host "Cleaning up test data..." -ForegroundColor Cyan
    Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId" -Method Delete -Headers @{Authorization = "Bearer $token"} -ErrorAction SilentlyContinue
    Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId2" -Method Delete -Headers @{Authorization = "Bearer $token"} -ErrorAction SilentlyContinue
    
} catch {
    Write-Host "Error in backtest comparison test: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Backtest service tests completed." -ForegroundColor Cyan
Write-Host "===== Backtest Service Test Complete =====" -ForegroundColor Cyan