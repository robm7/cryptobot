# Data Service Test Script (PowerShell)
# Tests data service functionality

# Set environment variables
$env:PYTHONPATH = (Get-Location).Path
$env:TEST_MODE = "true"

Write-Host "===== Data Service Test =====" -ForegroundColor Cyan
Write-Host "Starting data service tests..." -ForegroundColor Cyan

# Check if data service is running
Write-Host "Checking if data service is running..." -ForegroundColor Cyan
$dataProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*data/main.py*" }
if ($dataProcess) {
    Write-Host "Data service is running." -ForegroundColor Green
} else {
    Write-Host "Data service is not running. Starting data service..." -ForegroundColor Yellow
    # Start data service if not running
    & "$PSScriptRoot\..\non-docker-setup\start_data.ps1"
    Start-Sleep -Seconds 5  # Wait for service to start
}

# Run unit tests for data service
Write-Host "Running data service unit tests..." -ForegroundColor Cyan
python -m pytest tests/test_data_service.py -v

# Test data API endpoints
Write-Host "Testing data API endpoints..." -ForegroundColor Cyan
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

# Test historical data retrieval
Write-Host "Testing historical data retrieval..." -ForegroundColor Cyan
try {
    $historicalResponse = Invoke-RestMethod -Uri "http://localhost:8000/data/historical?symbol=BTCUSDT&timeframe=1h&limit=100" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
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

# Test OHLCV data retrieval
Write-Host "Testing OHLCV data retrieval..." -ForegroundColor Cyan
try {
    $ohlcvResponse = Invoke-RestMethod -Uri "http://localhost:8000/data/ohlcv?symbol=BTCUSDT&timeframe=1h&limit=100" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($ohlcvResponse.open) {
        Write-Host "Successfully retrieved OHLCV data." -ForegroundColor Green
    } else {
        Write-Host "Failed to retrieve OHLCV data." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to retrieve OHLCV data: $_" -ForegroundColor Red
    exit 1
}

# Test ticker data retrieval
Write-Host "Testing ticker data retrieval..." -ForegroundColor Cyan
try {
    $tickerResponse = Invoke-RestMethod -Uri "http://localhost:8000/data/ticker?symbol=BTCUSDT" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($tickerResponse.price) {
        Write-Host "Successfully retrieved ticker data." -ForegroundColor Green
    } else {
        Write-Host "Failed to retrieve ticker data." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to retrieve ticker data: $_" -ForegroundColor Red
    exit 1
}

# Test order book data retrieval
Write-Host "Testing order book data retrieval..." -ForegroundColor Cyan
try {
    $orderbookResponse = Invoke-RestMethod -Uri "http://localhost:8000/data/orderbook?symbol=BTCUSDT&limit=10" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction Stop
    
    if ($orderbookResponse.bids -and $orderbookResponse.asks) {
        Write-Host "Successfully retrieved order book data." -ForegroundColor Green
    } else {
        Write-Host "Failed to retrieve order book data." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to retrieve order book data: $_" -ForegroundColor Red
    exit 1
}

# Test data import
Write-Host "Testing data import..." -ForegroundColor Cyan
# Create a test CSV file with OHLCV data
$testCsvPath = "$env:TEMP\test_ohlcv.csv"
@"
timestamp,open,high,low,close,volume
2025-01-01T00:00:00Z,50000.0,51000.0,49500.0,50500.0,100.5
2025-01-01T01:00:00Z,50500.0,51500.0,50000.0,51000.0,120.3
2025-01-01T02:00:00Z,51000.0,52000.0,50800.0,51800.0,150.7
"@ | Out-File -FilePath $testCsvPath -Encoding utf8

$importMetadata = @{
    symbol = "BTCUSDT"
    timeframe = "1h"
    source = "file"
    format = "csv"
} | ConvertTo-Json

try {
    $form = @{
        data = Get-Item -Path $testCsvPath
        metadata = $importMetadata
    }
    
    $importResponse = Invoke-RestMethod -Uri "http://localhost:8000/data/import" -Method Post -Headers @{Authorization = "Bearer $token"} -Form $form -ErrorAction Stop
    
    if ($importResponse.imported) {
        Write-Host "Successfully imported data." -ForegroundColor Green
    } else {
        Write-Host "Failed to import data." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to import data: $_" -ForegroundColor Red
    exit 1
}

# Test data export
Write-Host "Testing data export..." -ForegroundColor Cyan
$exportData = @{
    symbol = "BTCUSDT"
    timeframe = "1h"
    start_time = "2025-01-01T00:00:00Z"
    end_time = "2025-01-01T03:00:00Z"
    format = "csv"
} | ConvertTo-Json

$exportedDataPath = "$env:TEMP\exported_data.csv"

try {
    $exportResponse = Invoke-RestMethod -Uri "http://localhost:8000/data/export" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $exportData -ErrorAction Stop -OutFile $exportedDataPath
    
    if (Test-Path $exportedDataPath) {
        $fileContent = Get-Content -Path $exportedDataPath
        if ($fileContent.Count -gt 1) {
            Write-Host "Successfully exported data." -ForegroundColor Green
        } else {
            Write-Host "Exported file is empty." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Failed to export data." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to export data: $_" -ForegroundColor Red
    exit 1
}

# Test data aggregation
Write-Host "Testing data aggregation..." -ForegroundColor Cyan
$aggregationData = @{
    symbol = "BTCUSDT"
    source_timeframe = "1h"
    target_timeframe = "4h"
    start_time = "2025-01-01T00:00:00Z"
    end_time = "2025-01-02T00:00:00Z"
} | ConvertTo-Json

try {
    $aggregateResponse = Invoke-RestMethod -Uri "http://localhost:8000/data/aggregate" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $aggregationData -ErrorAction Stop
    
    if ($aggregateResponse.aggregated) {
        Write-Host "Successfully aggregated data." -ForegroundColor Green
    } else {
        Write-Host "Failed to aggregate data." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to aggregate data: $_" -ForegroundColor Red
    exit 1
}

# Test data synchronization
Write-Host "Testing data synchronization..." -ForegroundColor Cyan
$syncData = @{
    symbol = "BTCUSDT"
    timeframe = "1h"
    exchange = "binance"
    start_time = "2025-01-01T00:00:00Z"
    end_time = "2025-01-02T00:00:00Z"
} | ConvertTo-Json

try {
    $syncResponse = Invoke-RestMethod -Uri "http://localhost:8000/data/sync" -Method Post -ContentType "application/json" -Headers @{Authorization = "Bearer $token"} -Body $syncData -ErrorAction Stop
    
    if ($syncResponse.sync) {
        Write-Host "Successfully initiated data synchronization." -ForegroundColor Green
    } else {
        Write-Host "Failed to initiate data synchronization." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Failed to initiate data synchronization: $_" -ForegroundColor Red
    exit 1
}

# Test data streaming
Write-Host "Testing data streaming..." -ForegroundColor Cyan
$streamOutputPath = "$env:TEMP\stream_output.txt"

try {
    # Start a background job to listen for streaming data
    $job = Start-Job -ScriptBlock {
        param($uri, $token, $outputPath)
        
        try {
            $response = Invoke-WebRequest -Uri $uri -Headers @{Authorization = "Bearer $token"} -Method Get -TimeoutSec 5
            $response.Content | Out-File -FilePath $outputPath
        } catch {
            "Error: $_" | Out-File -FilePath $outputPath
        }
    } -ArgumentList "http://localhost:8000/data/stream?symbol=BTCUSDT", $token, $streamOutputPath
    
    # Wait a few seconds to collect some data
    Start-Sleep -Seconds 5
    
    # Stop the job
    Stop-Job -Job $job
    Remove-Job -Job $job -Force
    
    # Check if we received any data
    if (Test-Path $streamOutputPath) {
        $streamContent = Get-Content -Path $streamOutputPath
        if ($streamContent.Count -gt 0) {
            Write-Host "Successfully received streaming data." -ForegroundColor Green
        } else {
            Write-Host "Stream output file is empty." -ForegroundColor Yellow
        }
    } else {
        Write-Host "Failed to receive streaming data." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error in data streaming test: $_" -ForegroundColor Red
    exit 1
}

# Clean up
Remove-Item -Path $testCsvPath -ErrorAction SilentlyContinue
Remove-Item -Path $exportedDataPath -ErrorAction SilentlyContinue
Remove-Item -Path $streamOutputPath -ErrorAction SilentlyContinue

Write-Host "Data service tests completed." -ForegroundColor Cyan
Write-Host "===== Data Service Test Complete =====" -ForegroundColor Cyan