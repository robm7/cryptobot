# Integration Test Script (PowerShell)
# Tests integration between different services

# Set environment variables
$env:PYTHONPATH = (Get-Location).Path
$env:TEST_MODE = "true"

Write-Host "===== Integration Test =====" -ForegroundColor Cyan
Write-Host "Starting integration tests..." -ForegroundColor Cyan

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

# Run integration tests
Write-Host "Running integration tests..." -ForegroundColor Cyan
python -m pytest tests/integration/test_auth_integration.py -v
python -m pytest tests/integration/test_service_integration.py -v
python -m pytest tests/integration/test_service_interactions.py -v

# Test end-to-end workflow
Write-Host "Testing end-to-end workflow..." -ForegroundColor Cyan

# Get auth token
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

# 1. Create a strategy
Write-Host "1. Creating a strategy..." -ForegroundColor Cyan
$strategyData = @{
    name = "Integration Test Strategy"
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

# 2. Run a backtest on the strategy
Write-Host "2. Running a backtest on the strategy..." -ForegroundColor Cyan
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

# Wait for backtest to complete
Write-Host "Waiting for backtest to complete..." -ForegroundColor Cyan
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

# 3. Get backtest results
Write-Host "3. Getting backtest results..." -ForegroundColor Cyan
try {
    $resultsResponse = Invoke-RestMethod -Uri "http://localhost:8000/backtest/$backtestId/results" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($resultsResponse.total_return -ne $null) {
        Write-Host "Successfully retrieved backtest results." -ForegroundColor Green
    } else {
        Write-Host "Failed to retrieve backtest results." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to retrieve backtest results: $_" -ForegroundColor Red
    exit 1
}

# 4. Execute the strategy
Write-Host "4. Executing the strategy..." -ForegroundColor Cyan
try {
    $executeResponse = Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId/execute" -Method Post -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    Write-Host "Successfully executed strategy." -ForegroundColor Green
} catch {
    Write-Host "Failed to execute strategy: $_" -ForegroundColor Red
    exit 1
}

# 5. Check for generated trades
Write-Host "5. Checking for generated trades..." -ForegroundColor Cyan
try {
    $tradesResponse = Invoke-RestMethod -Uri "http://localhost:8000/trades?strategy_id=$strategyId" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($tradesResponse.trades) {
        Write-Host "Successfully retrieved trades for strategy." -ForegroundColor Green
    } else {
        Write-Host "Failed to retrieve trades for strategy." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to retrieve trades for strategy: $_" -ForegroundColor Red
    exit 1
}

# 6. Test data flow between services
Write-Host "6. Testing data flow between services..." -ForegroundColor Cyan
# Request historical data
try {
    $historicalResponse = Invoke-RestMethod -Uri "http://localhost:8000/data/historical?symbol=BTCUSDT&timeframe=1h&limit=10" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($historicalResponse.data) {
        Write-Host "Successfully retrieved historical data." -ForegroundColor Green
    } else {
        Write-Host "Failed to retrieve historical data." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to retrieve historical data: $_" -ForegroundColor Red
    exit 1
}

# Use the data to create a signal
$signalData = @{
    symbol = "BTCUSDT"
    side = "buy"
    price = 50000.0
    quantity = 0.01
    strategy_id = $strategyId
    signal_type = "entry"
} | ConvertTo-Json

try {
    $signalResponse = Invoke-RestMethod -Uri "http://localhost:8000/trade/execute" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $signalData -ErrorAction Stop
    
    if ($signalResponse.trade_id) {
        Write-Host "Successfully executed trade signal." -ForegroundColor Green
        $tradeId = $signalResponse.trade_id
    } else {
        Write-Host "Failed to execute trade signal." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to execute trade signal: $_" -ForegroundColor Red
    exit 1
}

# 7. Test cross-service authentication
Write-Host "7. Testing cross-service authentication..." -ForegroundColor Cyan
# Refresh token
try {
    $refreshToken = $authResponse.refresh_token
    
    $refreshBody = @{
        refresh_token = $refreshToken
    } | ConvertTo-Json
    
    $refreshResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/refresh" -Method Post -ContentType "application/json" -Body $refreshBody -ErrorAction Stop
    $newToken = $refreshResponse.access_token
    
    if (-not $newToken) {
        Write-Host "Failed to refresh token." -ForegroundColor Red
        exit 1
    } else {
        Write-Host "Successfully refreshed token." -ForegroundColor Green
        
        # Test the new token with a protected endpoint
        $testResponse = Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId" -Method Get -Headers @{Authorization = "Bearer $newToken"} -ErrorAction Stop
        
        if ($testResponse.name -eq "Integration Test Strategy") {
            Write-Host "Successfully authenticated with new token." -ForegroundColor Green
        } else {
            Write-Host "Failed to authenticate with new token." -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "Error in cross-service authentication test: $_" -ForegroundColor Red
    exit 1
}

# 8. Clean up
Write-Host "8. Cleaning up..." -ForegroundColor Cyan
try {
    Invoke-RestMethod -Uri "http://localhost:8000/strategy/$strategyId" -Method Delete -Headers @{Authorization = "Bearer $token"} -ErrorAction SilentlyContinue
} catch {
    Write-Host "Error during cleanup: $_" -ForegroundColor Yellow
}

Write-Host "Integration tests completed." -ForegroundColor Cyan
Write-Host "===== Integration Test Complete =====" -ForegroundColor Cyan