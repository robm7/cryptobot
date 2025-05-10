# Master Test Script (PowerShell)
# Runs all test scripts and generates a comprehensive report

# Set environment variables
$env:PYTHONPATH = (Get-Location).Path
$env:TEST_MODE = "true"

Write-Host "===== Master Test Script =====" -ForegroundColor Cyan
Write-Host "Running all tests and generating reports..." -ForegroundColor Cyan

# Create output directory for logs
$logDir = "test_logs"
if (-not (Test-Path -Path $logDir)) {
    New-Item -Path $logDir -ItemType Directory | Out-Null
}

# Get current timestamp for log filenames
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$masterLog = "$logDir\master_test_log_$timestamp.txt"

# Function to run a test script and log results
function Run-TestScript {
    param (
        [string]$Script,
        [string]$Name
    )
    
    $logFile = "$logDir\${Name}_test_log_$timestamp.txt"
    
    Write-Host "Running $Name tests..." -ForegroundColor Cyan
    "===============================================" | Out-File -FilePath $masterLog -Append
    "Running $Name tests at $(Get-Date)" | Out-File -FilePath $masterLog -Append
    "===============================================" | Out-File -FilePath $masterLog -Append
    
    # Run the test script and capture output
    $output = & "$PSScriptRoot\$Script" 2>&1
    $exitCode = $LASTEXITCODE
    
    # Save output to log file
    $output | Out-File -FilePath $logFile
    
    # Append log to master log
    Get-Content -Path $logFile | Out-File -FilePath $masterLog -Append
    
    # Check if test passed or failed
    if ($exitCode -eq 0) {
        Write-Host "✅ $Name tests completed successfully." -ForegroundColor Green
        "✅ $Name tests completed successfully." | Out-File -FilePath $masterLog -Append
        return $true
    } else {
        Write-Host "❌ $Name tests failed with exit code $exitCode." -ForegroundColor Red
        "❌ $Name tests failed with exit code $exitCode." | Out-File -FilePath $masterLog -Append
        return $false
    }
    
    "" | Out-File -FilePath $masterLog -Append
}

# Initialize counters
$totalTests = 0
$passedTests = 0
$failedTests = 0

# Start the master log
"===== Cryptobot Test Suite =====" | Out-File -FilePath $masterLog
"Started at: $(Get-Date)" | Out-File -FilePath $masterLog
"Environment: $((Get-WmiObject -Class Win32_OperatingSystem).Caption) $(Get-WmiObject -Class Win32_OperatingSystem).Version" | Out-File -FilePath $masterLog
"" | Out-File -FilePath $masterLog

# Check if all services are running
Write-Host "Checking if all services are running..." -ForegroundColor Cyan
"Checking if all services are running..." | Out-File -FilePath $masterLog -Append

$authProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*auth/main.py*" }
if (-not $authProcess) {
    Write-Host "Auth service is not running. Starting auth service..." -ForegroundColor Yellow
    "Auth service is not running. Starting auth service..." | Out-File -FilePath $masterLog -Append
    & "$PSScriptRoot\..\non-docker-setup\start_auth.ps1"
    Start-Sleep -Seconds 5
}

$strategyProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*strategy/main.py*" }
if (-not $strategyProcess) {
    Write-Host "Strategy service is not running. Starting strategy service..." -ForegroundColor Yellow
    "Strategy service is not running. Starting strategy service..." | Out-File -FilePath $masterLog -Append
    & "$PSScriptRoot\..\non-docker-setup\start_strategy.ps1"
    Start-Sleep -Seconds 5
}

$backtestProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*backtest/main.py*" }
if (-not $backtestProcess) {
    Write-Host "Backtest service is not running. Starting backtest service..." -ForegroundColor Yellow
    "Backtest service is not running. Starting backtest service..." | Out-File -FilePath $masterLog -Append
    & "$PSScriptRoot\..\non-docker-setup\start_backtest.ps1"
    Start-Sleep -Seconds 5
}

$tradeProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*trade/main.py*" }
if (-not $tradeProcess) {
    Write-Host "Trade service is not running. Starting trade service..." -ForegroundColor Yellow
    "Trade service is not running. Starting trade service..." | Out-File -FilePath $masterLog -Append
    & "$PSScriptRoot\..\non-docker-setup\start_trade.ps1"
    Start-Sleep -Seconds 5
}

$dataProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*data/main.py*" }
if (-not $dataProcess) {
    Write-Host "Data service is not running. Starting data service..." -ForegroundColor Yellow
    "Data service is not running. Starting data service..." | Out-File -FilePath $masterLog -Append
    & "$PSScriptRoot\..\non-docker-setup\start_data.ps1"
    Start-Sleep -Seconds 5
}

Write-Host "All services are running." -ForegroundColor Green
"All services are running." | Out-File -FilePath $masterLog -Append
"" | Out-File -FilePath $masterLog -Append

# Run individual service tests
Write-Host "Running individual service tests..." -ForegroundColor Cyan
"Running individual service tests..." | Out-File -FilePath $masterLog -Append

# Auth service tests
$totalTests++
if (Run-TestScript -Script "test_auth.ps1" -Name "auth") {
    $passedTests++
} else {
    $failedTests++
}

# Strategy service tests
$totalTests++
if (Run-TestScript -Script "test_strategy.ps1" -Name "strategy") {
    $passedTests++
} else {
    $failedTests++
}

# Backtest service tests
$totalTests++
if (Run-TestScript -Script "test_backtest.ps1" -Name "backtest") {
    $passedTests++
} else {
    $failedTests++
}

# Trade service tests
$totalTests++
if (Run-TestScript -Script "test_trade.ps1" -Name "trade") {
    $passedTests++
} else {
    $failedTests++
}

# Data service tests
$totalTests++
if (Run-TestScript -Script "test_data.ps1" -Name "data") {
    $passedTests++
} else {
    $failedTests++
}

# Run integration tests
Write-Host "Running integration tests..." -ForegroundColor Cyan
"Running integration tests..." | Out-File -FilePath $masterLog -Append

$totalTests++
if (Run-TestScript -Script "test_integration.ps1" -Name "integration") {
    $passedTests++
} else {
    $failedTests++
}

# Run performance tests
Write-Host "Running performance tests..." -ForegroundColor Cyan
"Running performance tests..." | Out-File -FilePath $masterLog -Append

$totalTests++
if (Run-TestScript -Script "test_performance.ps1" -Name "performance") {
    $passedTests++
} else {
    $failedTests++
}

# Generate test report
Write-Host "Generating test report..." -ForegroundColor Cyan
"Generating test report..." | Out-File -FilePath $masterLog -Append

$totalTests++
if (Run-TestScript -Script "generate_test_report.ps1" -Name "report") {
    $passedTests++
} else {
    $failedTests++
}

# Run performance optimization
Write-Host "Running performance optimization..." -ForegroundColor Cyan
"Running performance optimization..." | Out-File -FilePath $masterLog -Append

$totalTests++
if (Run-TestScript -Script "optimize_performance.ps1" -Name "optimization") {
    $passedTests++
} else {
    $failedTests++
}

# Calculate success rate
$successRate = [math]::Round(($passedTests * 100 / $totalTests), 2)

# Print summary
Write-Host ""
Write-Host "===== Test Summary =====" -ForegroundColor Cyan
Write-Host "Total tests: $totalTests" -ForegroundColor Cyan
Write-Host "Passed tests: $passedTests" -ForegroundColor Green
Write-Host "Failed tests: $failedTests" -ForegroundColor Red
Write-Host "Success rate: $successRate%" -ForegroundColor Cyan

# Add summary to master log
"" | Out-File -FilePath $masterLog -Append
"===== Test Summary =====" | Out-File -FilePath $masterLog -Append
"Total tests: $totalTests" | Out-File -FilePath $masterLog -Append
"Passed tests: $passedTests" | Out-File -FilePath $masterLog -Append
"Failed tests: $failedTests" | Out-File -FilePath $masterLog -Append
"Success rate: $successRate%" | Out-File -FilePath $masterLog -Append
"Completed at: $(Get-Date)" | Out-File -FilePath $masterLog -Append

Write-Host "Master log file: $masterLog" -ForegroundColor Cyan
Write-Host "All tests completed." -ForegroundColor Cyan
Write-Host "===== Master Test Script Complete =====" -ForegroundColor Cyan