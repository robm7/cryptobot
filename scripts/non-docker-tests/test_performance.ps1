# Performance Test Script (PowerShell)
# Tests performance of various services and identifies bottlenecks

# Set environment variables
$env:PYTHONPATH = (Get-Location).Path
$env:TEST_MODE = "true"

Write-Host "===== Performance Test =====" -ForegroundColor Cyan
Write-Host "Starting performance tests..." -ForegroundColor Cyan

# Check if all services are running
Write-Host "Checking if all services are running..." -ForegroundColor Cyan

$authProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*auth/main.py*" }
if (-not $authProcess) {
    Write-Host "Auth service is not running. Starting auth service..." -ForegroundColor Yellow
    & "$PSScriptRoot\..\non-docker-setup\start_auth.ps1"
    Start-Sleep -Seconds 5
}

$strategyProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*strategy/main.py*" }
if (-not $strategyProcess) {
    Write-Host "Strategy service is not running. Starting strategy service..." -ForegroundColor Yellow
    & "$PSScriptRoot\..\non-docker-setup\start_strategy.ps1"
    Start-Sleep -Seconds 5
}

$backtestProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*backtest/main.py*" }
if (-not $backtestProcess) {
    Write-Host "Backtest service is not running. Starting backtest service..." -ForegroundColor Yellow
    & "$PSScriptRoot\..\non-docker-setup\start_backtest.ps1"
    Start-Sleep -Seconds 5
}

$tradeProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*trade/main.py*" }
if (-not $tradeProcess) {
    Write-Host "Trade service is not running. Starting trade service..." -ForegroundColor Yellow
    & "$PSScriptRoot\..\non-docker-setup\start_trade.ps1"
    Start-Sleep -Seconds 5
}

$dataProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*data/main.py*" }
if (-not $dataProcess) {
    Write-Host "Data service is not running. Starting data service..." -ForegroundColor Yellow
    & "$PSScriptRoot\..\non-docker-setup\start_data.ps1"
    Start-Sleep -Seconds 5
}

# Run performance benchmark tests
Write-Host "Running performance benchmark tests..." -ForegroundColor Cyan
python -m pytest tests/benchmarks/test_performance.py -v

# Get auth token for API tests
Write-Host "Getting auth token for API tests..." -ForegroundColor Cyan
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

# Test auth service performance
Write-Host "Testing auth service performance..." -ForegroundColor Cyan
Write-Host "Running 100 authentication requests..." -ForegroundColor Cyan
$startTime = Get-Date

for ($i = 1; $i -le 100; $i++) {
    try {
        Invoke-RestMethod -Uri "http://localhost:8000/auth/login" -Method Post -ContentType "application/json" -Body $loginBody -ErrorAction SilentlyContinue | Out-Null
    } catch {
        # Ignore errors during performance testing
    }
}

$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds
$requestsPerSecond = 100 / $duration

Write-Host "Auth service performance: $([math]::Round($requestsPerSecond, 2)) requests/second" -ForegroundColor Green
Write-Host "Average response time: $([math]::Round($duration / 100, 4)) seconds" -ForegroundColor Green

# Test data service performance
Write-Host "Testing data service performance..." -ForegroundColor Cyan
Write-Host "Running 100 historical data requests..." -ForegroundColor Cyan
$startTime = Get-Date

for ($i = 1; $i -le 100; $i++) {
    try {
        Invoke-RestMethod -Uri "http://localhost:8000/data/historical?symbol=BTCUSDT&timeframe=1h&limit=10" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction SilentlyContinue | Out-Null
    } catch {
        # Ignore errors during performance testing
    }
}

$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds
$dataRequestsPerSecond = 100 / $duration

Write-Host "Data service performance: $([math]::Round($dataRequestsPerSecond, 2)) requests/second" -ForegroundColor Green
Write-Host "Average response time: $([math]::Round($duration / 100, 4)) seconds" -ForegroundColor Green

# Test strategy service performance
Write-Host "Testing strategy service performance..." -ForegroundColor Cyan
Write-Host "Creating test strategy..." -ForegroundColor Cyan
$strategyData = @{
    name = "Performance Test Strategy"
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
    }
} catch {
    Write-Host "Failed to create strategy: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Running 50 strategy execution requests..." -ForegroundColor Cyan
$startTime = Get-Date

for ($i = 1; $i -le 50; $i++) {
    try {
        Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId/execute" -Method Post -Headers @{Authorization = "Bearer $token"} -ErrorAction SilentlyContinue | Out-Null
    } catch {
        # Ignore errors during performance testing
    }
}

$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds
$strategyRequestsPerSecond = 50 / $duration

Write-Host "Strategy service performance: $([math]::Round($strategyRequestsPerSecond, 2)) requests/second" -ForegroundColor Green
Write-Host "Average response time: $([math]::Round($duration / 50, 4)) seconds" -ForegroundColor Green

# Test trade service performance
Write-Host "Testing trade service performance..." -ForegroundColor Cyan
Write-Host "Running 50 trade creation requests..." -ForegroundColor Cyan
$tradeData = @{
    symbol = "BTCUSDT"
    side = "buy"
    type = "limit"
    quantity = 0.01
    price = 50000.0
    strategy_id = $strategyId
    exchange = "binance"
} | ConvertTo-Json

$startTime = Get-Date

for ($i = 1; $i -le 50; $i++) {
    try {
        Invoke-RestMethod -Uri "http://localhost:8000/trade" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $tradeData -ErrorAction SilentlyContinue | Out-Null
    } catch {
        # Ignore errors during performance testing
    }
}

$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds
$tradeRequestsPerSecond = 50 / $duration

Write-Host "Trade service performance: $([math]::Round($tradeRequestsPerSecond, 2)) requests/second" -ForegroundColor Green
Write-Host "Average response time: $([math]::Round($duration / 50, 4)) seconds" -ForegroundColor Green

# Test backtest service performance
Write-Host "Testing backtest service performance..." -ForegroundColor Cyan
Write-Host "Running 10 backtest requests..." -ForegroundColor Cyan
$backtestData = @{
    strategy_id = $strategyId
    start_date = "2025-01-01T00:00:00Z"
    end_date = "2025-01-31T23:59:59Z"
    initial_capital = 10000
    symbols = @("BTCUSDT")
    timeframe = "1h"
} | ConvertTo-Json

$startTime = Get-Date

for ($i = 1; $i -le 10; $i++) {
    try {
        Invoke-RestMethod -Uri "http://localhost:8000/backtest" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $backtestData -ErrorAction SilentlyContinue | Out-Null
    } catch {
        # Ignore errors during performance testing
    }
}

$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds
$backtestRequestsPerSecond = 10 / $duration

Write-Host "Backtest service performance: $([math]::Round($backtestRequestsPerSecond, 2)) requests/second" -ForegroundColor Green
Write-Host "Average response time: $([math]::Round($duration / 10, 4)) seconds" -ForegroundColor Green

# Test concurrent user load
Write-Host "Testing concurrent user load..." -ForegroundColor Cyan
Write-Host "Simulating 10 concurrent users making requests..." -ForegroundColor Cyan

# Create a function to simulate user activity
function Simulate-User {
    param (
        [int]$UserId,
        [string]$Token,
        [int]$StrategyId
    )
    
    try {
        # Make a series of requests
        Invoke-RestMethod -Uri "http://localhost:8000/data/historical?symbol=BTCUSDT&timeframe=1h&limit=10" -Method Get -Headers @{Authorization = "Bearer $Token"} -ErrorAction SilentlyContinue | Out-Null
        Invoke-RestMethod -Uri "http://localhost:8000/strategy/$StrategyId" -Method Get -Headers @{Authorization = "Bearer $Token"} -ErrorAction SilentlyContinue | Out-Null
        Invoke-RestMethod -Uri "http://localhost:8000/trades?limit=10" -Method Get -Headers @{Authorization = "Bearer $Token"} -ErrorAction SilentlyContinue | Out-Null
        
        return "User $UserId completed requests"
    } catch {
        return "User $UserId encountered an error: $_"
    }
}

$startTime = Get-Date

# Start 10 jobs to simulate concurrent users
$jobs = @()
for ($i = 1; $i -le 10; $i++) {
    $jobs += Start-Job -ScriptBlock {
        param($userId, $token, $strategyId)
        
        # Make a series of requests
        try {
            Invoke-RestMethod -Uri "http://localhost:8000/data/historical?symbol=BTCUSDT&timeframe=1h&limit=10" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction SilentlyContinue | Out-Null
            Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction SilentlyContinue | Out-Null
            Invoke-RestMethod -Uri "http://localhost:8000/trades?limit=10" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction SilentlyContinue | Out-Null
            
            return "User $userId completed requests"
        } catch {
            return "User $userId encountered an error: $_"
        }
    } -ArgumentList $i, $token, $strategyId
}

# Wait for all jobs to complete
$results = $jobs | Wait-Job | Receive-Job
$jobs | Remove-Job

$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds

Write-Host "Concurrent user test completed in $([math]::Round($duration, 2)) seconds" -ForegroundColor Green
Write-Host "Average time per user: $([math]::Round($duration / 10, 4)) seconds" -ForegroundColor Green

# Test system resource usage
Write-Host "Testing system resource usage..." -ForegroundColor Cyan
Write-Host "CPU usage during load test:" -ForegroundColor Cyan
Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 5 | ForEach-Object { $_.CounterSamples[0].CookedValue }

Write-Host "Memory usage during load test:" -ForegroundColor Cyan
Get-Counter '\Memory\Available MBytes' -SampleInterval 1 -MaxSamples 5 | ForEach-Object { $_.CounterSamples[0].CookedValue }

Write-Host "Disk I/O during load test:" -ForegroundColor Cyan
Get-Counter '\PhysicalDisk(_Total)\Disk Reads/sec', '\PhysicalDisk(_Total)\Disk Writes/sec' -SampleInterval 1 -MaxSamples 5

# Clean up
Write-Host "Cleaning up..." -ForegroundColor Cyan
try {
    Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId" -Method Delete -Headers @{Authorization = "Bearer $token"} -ErrorAction SilentlyContinue
} catch {
    Write-Host "Error during cleanup: $_" -ForegroundColor Yellow
}

# Generate performance report
Write-Host "Generating performance report..." -ForegroundColor Cyan
$reportContent = @"
# Performance Test Report

## Summary
- Auth Service: $([math]::Round($requestsPerSecond, 2)) requests/second
- Data Service: $([math]::Round($dataRequestsPerSecond, 2)) requests/second
- Strategy Service: $([math]::Round($strategyRequestsPerSecond, 2)) requests/second
- Trade Service: $([math]::Round($tradeRequestsPerSecond, 2)) requests/second
- Backtest Service: $([math]::Round($backtestRequestsPerSecond, 2)) requests/second

## Concurrent User Load
- 10 concurrent users completed in $([math]::Round($duration, 2)) seconds
- Average time per user: $([math]::Round($duration / 10, 4)) seconds

## Recommendations
- Monitor CPU usage during peak loads
- Consider scaling services with higher response times
- Implement caching for frequently accessed data
- Optimize database queries for better performance
"@

$reportContent | Out-File -FilePath "performance_report.md" -Encoding utf8

Write-Host "Performance report generated: performance_report.md" -ForegroundColor Green
Write-Host "Performance tests completed." -ForegroundColor Cyan
Write-Host "===== Performance Test Complete =====" -ForegroundColor Cyan