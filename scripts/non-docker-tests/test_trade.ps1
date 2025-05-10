# Trade Service Test Script (PowerShell)
# Tests trade service functionality

# Set environment variables
$env:PYTHONPATH = (Get-Location).Path
$env:TEST_MODE = "true"

Write-Host "===== Trade Service Test =====" -ForegroundColor Cyan
Write-Host "Starting trade service tests..." -ForegroundColor Cyan

# Check if trade service is running
Write-Host "Checking if trade service is running..." -ForegroundColor Cyan
$tradeProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*trade/main.py*" }
if ($tradeProcess) {
    Write-Host "Trade service is running." -ForegroundColor Green
} else {
    Write-Host "Trade service is not running. Starting trade service..." -ForegroundColor Yellow
    # Start trade service if not running
    & "$PSScriptRoot\..\non-docker-setup\start_trade.ps1"
    Start-Sleep -Seconds 5  # Wait for service to start
}

# Run unit tests for trade service
Write-Host "Running trade service unit tests..." -ForegroundColor Cyan
python -m pytest tests/test_trades.py -v
python -m pytest tests/test_trade_execution.py -v

# Test trade API endpoints
Write-Host "Testing trade API endpoints..." -ForegroundColor Cyan
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

# Test trade creation
Write-Host "Testing trade creation..." -ForegroundColor Cyan
$tradeData = @{
    symbol = "BTCUSDT"
    side = "buy"
    type = "limit"
    quantity = 0.01
    price = 50000.0
    strategy_id = 1
    exchange = "binance"
} | ConvertTo-Json

try {
    $createResponse = Invoke-RestMethod -Uri "http://localhost:8000/trade" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $tradeData -ErrorAction Stop
    $tradeId = $createResponse.id
    
    if (-not $tradeId) {
        Write-Host "Failed to create trade." -ForegroundColor Red
        exit 1
    } else {
        Write-Host "Successfully created trade with ID: $tradeId" -ForegroundColor Green
    }
} catch {
    Write-Host "Failed to create trade: $_" -ForegroundColor Red
    exit 1
}

# Test trade retrieval
Write-Host "Testing trade retrieval..." -ForegroundColor Cyan
try {
    $getResponse = Invoke-RestMethod -Uri "http://localhost:8000/trade/$tradeId" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($getResponse.symbol -eq "BTCUSDT") {
        Write-Host "Successfully retrieved trade." -ForegroundColor Green
    } else {
        Write-Host "Failed to retrieve trade." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to retrieve trade: $_" -ForegroundColor Red
    exit 1
}

# Test trade update
Write-Host "Testing trade update..." -ForegroundColor Cyan
$updateData = @{
    status = "filled"
    filled_quantity = 0.01
    filled_price = 50005.0
    fill_time = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json

try {
    $updateResponse = Invoke-RestMethod -Uri "http://localhost:8000/trade/$tradeId" -Method Put -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $updateData -ErrorAction Stop
    Write-Host "Successfully updated trade." -ForegroundColor Green
} catch {
    Write-Host "Failed to update trade: $_" -ForegroundColor Red
    exit 1
}

# Test trade cancellation
Write-Host "Testing trade cancellation..." -ForegroundColor Cyan
$cancelData = @{
    reason = "test_cancellation"
} | ConvertTo-Json

try {
    $cancelResponse = Invoke-RestMethod -Uri "http://localhost:8000/trade/$tradeId/cancel" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $cancelData -ErrorAction Stop
    Write-Host "Successfully cancelled trade." -ForegroundColor Green
} catch {
    Write-Host "Failed to cancel trade: $_" -ForegroundColor Red
    exit 1
}

# Test trade list retrieval
Write-Host "Testing trade list retrieval..." -ForegroundColor Cyan
try {
    $listResponse = Invoke-RestMethod -Uri "http://localhost:8000/trades" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($listResponse.trades) {
        Write-Host "Successfully retrieved trade list." -ForegroundColor Green
    } else {
        Write-Host "Failed to retrieve trade list." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to retrieve trade list: $_" -ForegroundColor Red
    exit 1
}

# Test trade filtering
Write-Host "Testing trade filtering..." -ForegroundColor Cyan
try {
    $filterResponse = Invoke-RestMethod -Uri "http://localhost:8000/trades?symbol=BTCUSDT&side=buy" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($filterResponse.trades) {
        Write-Host "Successfully filtered trades." -ForegroundColor Green
    } else {
        Write-Host "Failed to filter trades." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to filter trades: $_" -ForegroundColor Red
    exit 1
}

# Test trade statistics
Write-Host "Testing trade statistics..." -ForegroundColor Cyan
try {
    $statsResponse = Invoke-RestMethod -Uri "http://localhost:8000/trades/stats" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($statsResponse.total_trades -ne $null) {
        Write-Host "Successfully retrieved trade statistics." -ForegroundColor Green
    } else {
        Write-Host "Failed to retrieve trade statistics." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to retrieve trade statistics: $_" -ForegroundColor Red
    exit 1
}

# Test trade execution reliability
Write-Host "Testing trade execution reliability..." -ForegroundColor Cyan
# Create multiple trades in rapid succession
$tradeData = @{
    symbol = "BTCUSDT"
    side = "buy"
    type = "limit"
    quantity = 0.01
    price = 50000.0
    strategy_id = 1
    exchange = "binance"
} | ConvertTo-Json

try {
    for ($i = 1; $i -le 5; $i++) {
        Invoke-RestMethod -Uri "http://localhost:8000/trade" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $tradeData -ErrorAction Stop | Out-Null
    }
    
    # Check if all trades were created
    $listResponse = Invoke-RestMethod -Uri "http://localhost:8000/trades?limit=10" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($listResponse.trades.Count -ge 5) {
        Write-Host "Successfully created multiple trades." -ForegroundColor Green
    } else {
        Write-Host "Failed to create multiple trades." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error in trade execution reliability test: $_" -ForegroundColor Red
    exit 1
}

# Test trade execution service
Write-Host "Testing trade execution service..." -ForegroundColor Cyan
$signalData = @{
    symbol = "BTCUSDT"
    side = "buy"
    price = 50000.0
    quantity = 0.01
    strategy_id = 1
    signal_type = "entry"
} | ConvertTo-Json

try {
    $executeResponse = Invoke-RestMethod -Uri "http://localhost:8000/trade/execute" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $signalData -ErrorAction Stop
    
    if ($executeResponse.trade_id) {
        Write-Host "Successfully executed trade signal." -ForegroundColor Green
    } else {
        Write-Host "Failed to execute trade signal." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to execute trade signal: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Trade service tests completed." -ForegroundColor Cyan
Write-Host "===== Trade Service Test Complete =====" -ForegroundColor Cyan