# Strategy Service Test Script (PowerShell)
# Tests strategy service functionality

# Set environment variables
$env:PYTHONPATH = (Get-Location).Path
$env:TEST_MODE = "true"

Write-Host "===== Strategy Service Test =====" -ForegroundColor Cyan
Write-Host "Starting strategy service tests..." -ForegroundColor Cyan

# Check if strategy service is running
Write-Host "Checking if strategy service is running..." -ForegroundColor Cyan
$strategyProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*strategy/main.py*" }
if ($strategyProcess) {
    Write-Host "Strategy service is running." -ForegroundColor Green
} else {
    Write-Host "Strategy service is not running. Starting strategy service..." -ForegroundColor Yellow
    # Start strategy service if not running
    & "$PSScriptRoot\..\non-docker-setup\start_strategy.ps1"
    Start-Sleep -Seconds 5  # Wait for service to start
}

# Run unit tests for strategy service
Write-Host "Running strategy service unit tests..." -ForegroundColor Cyan
python -m pytest tests/test_base_strategy.py -v
python -m pytest tests/test_strategy_endpoints.py -v
python -m pytest tests/test_strategy_execution.py -v

# Test strategy creation
Write-Host "Testing strategy creation..." -ForegroundColor Cyan
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

# Create a test strategy
$strategyData = @{
    name = "Test Mean Reversion"
    type = "mean_reversion"
    parameters = @{
        window = 20
        deviation_threshold = 2.0
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
        Write-Host "Failed to create strategy." -ForegroundColor Red
        exit 1
    } else {
        Write-Host "Successfully created strategy with ID: $strategyId" -ForegroundColor Green
    }
} catch {
    Write-Host "Failed to create strategy: $_" -ForegroundColor Red
    exit 1
}

# Test strategy retrieval
Write-Host "Testing strategy retrieval..." -ForegroundColor Cyan
try {
    $getResponse = Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($getResponse.name -eq "Test Mean Reversion") {
        Write-Host "Successfully retrieved strategy." -ForegroundColor Green
    } else {
        Write-Host "Failed to retrieve strategy." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to retrieve strategy: $_" -ForegroundColor Red
    exit 1
}

# Test strategy update
Write-Host "Testing strategy update..." -ForegroundColor Cyan
$updateData = @{
    parameters = @{
        window = 25
        deviation_threshold = 2.5
        take_profit = 0.06
        stop_loss = 0.04
    }
    status = "paused"
} | ConvertTo-Json

try {
    $updateResponse = Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId" -Method Put -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $updateData -ErrorAction Stop
    Write-Host "Successfully updated strategy." -ForegroundColor Green
} catch {
    Write-Host "Failed to update strategy: $_" -ForegroundColor Red
    exit 1
}

# Test strategy execution
Write-Host "Testing strategy execution..." -ForegroundColor Cyan
try {
    $executeResponse = Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId/execute" -Method Post -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    Write-Host "Successfully executed strategy." -ForegroundColor Green
} catch {
    Write-Host "Failed to execute strategy: $_" -ForegroundColor Red
    exit 1
}

# Test strategy backtest
Write-Host "Testing strategy backtest..." -ForegroundColor Cyan
$backtestData = @{
    start_date = "2025-01-01T00:00:00Z"
    end_date = "2025-01-31T23:59:59Z"
    initial_capital = 10000
    symbols = @("BTCUSDT")
    timeframe = "1h"
} | ConvertTo-Json

try {
    $backtestResponse = Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId/backtest" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $backtestData -ErrorAction Stop
    
    if ($backtestResponse.backtest_id) {
        Write-Host "Successfully started backtest." -ForegroundColor Green
    } else {
        Write-Host "Failed to start backtest." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to start backtest: $_" -ForegroundColor Red
    exit 1
}

# Test strategy deletion
Write-Host "Testing strategy deletion..." -ForegroundColor Cyan
try {
    $deleteResponse = Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId" -Method Delete -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    Write-Host "Successfully deleted strategy." -ForegroundColor Green
} catch {
    Write-Host "Failed to delete strategy: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Strategy service tests completed." -ForegroundColor Cyan
Write-Host "===== Strategy Service Test Complete =====" -ForegroundColor Cyan