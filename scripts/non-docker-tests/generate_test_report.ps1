# Test Result Reporting Script (PowerShell)
# Generates comprehensive test reports from test results

# Set environment variables
$env:PYTHONPATH = (Get-Location).Path

Write-Host "===== Test Result Report Generation =====" -ForegroundColor Cyan
Write-Host "Generating test reports..." -ForegroundColor Cyan

# Create output directory for reports
$reportDir = "test_reports"
if (-not (Test-Path -Path $reportDir)) {
    New-Item -Path $reportDir -ItemType Directory | Out-Null
}

# Get current timestamp for report filenames
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$reportFile = "$reportDir\test_report_$timestamp.md"
$htmlReportFile = "$reportDir\test_report_$timestamp.html"
$jsonReportFile = "$reportDir\test_report_$timestamp.json"

# Function to run tests and capture results
function Run-TestsAndCapture {
    param (
        [string]$Service
    )
    
    $outputFile = "$reportDir\${Service}_test_output.txt"
    
    Write-Host "Running tests for $Service service..." -ForegroundColor Cyan
    & "$PSScriptRoot\test_$Service.ps1" > $outputFile 2>&1
    
    # Extract test results
    $content = Get-Content -Path $outputFile -Raw
    $totalTests = ([regex]::Matches($content, "test")).Count
    $passedTests = ([regex]::Matches($content, "PASSED")).Count
    $failedTests = ([regex]::Matches($content, "FAILED")).Count
    $skippedTests = ([regex]::Matches($content, "SKIPPED")).Count
    
    # Calculate success rate
    $successRate = 0
    if ($totalTests -gt 0) {
        $successRate = [math]::Round(($passedTests * 100 / $totalTests), 2)
    }
    
    # Return results as PSObject
    return [PSCustomObject]@{
        service = $Service
        total = $totalTests
        passed = $passedTests
        failed = $failedTests
        skipped = $skippedTests
        success_rate = $successRate
    }
}

# Function to run performance tests and capture results
function Run-PerformanceTests {
    $outputFile = "$reportDir\performance_test_output.txt"
    
    Write-Host "Running performance tests..." -ForegroundColor Cyan
    & "$PSScriptRoot\test_performance.ps1" > $outputFile 2>&1
    
    # Extract performance metrics
    $content = Get-Content -Path $outputFile -Raw
    
    $authRps = 0
    if ($content -match "Auth service performance: (\d+\.?\d*)") {
        $authRps = [double]$Matches[1]
    }
    
    $dataRps = 0
    if ($content -match "Data service performance: (\d+\.?\d*)") {
        $dataRps = [double]$Matches[1]
    }
    
    $strategyRps = 0
    if ($content -match "Strategy service performance: (\d+\.?\d*)") {
        $strategyRps = [double]$Matches[1]
    }
    
    $tradeRps = 0
    if ($content -match "Trade service performance: (\d+\.?\d*)") {
        $tradeRps = [double]$Matches[1]
    }
    
    $backtestRps = 0
    if ($content -match "Backtest service performance: (\d+\.?\d*)") {
        $backtestRps = [double]$Matches[1]
    }
    
    # Return results as PSObject
    return [PSCustomObject]@{
        auth_rps = $authRps
        data_rps = $dataRps
        strategy_rps = $strategyRps
        trade_rps = $tradeRps
        backtest_rps = $backtestRps
    }
}

# Function to run integration tests and capture results
function Run-IntegrationTests {
    $outputFile = "$reportDir\integration_test_output.txt"
    
    Write-Host "Running integration tests..." -ForegroundColor Cyan
    & "$PSScriptRoot\test_integration.ps1" > $outputFile 2>&1
    
    # Extract integration test results
    $content = Get-Content -Path $outputFile -Raw
    $totalTests = ([regex]::Matches($content, "test")).Count
    $passedTests = ([regex]::Matches($content, "Successfully")).Count
    $failedTests = ([regex]::Matches($content, "Failed")).Count
    
    # Calculate success rate
    $successRate = 0
    if ($totalTests -gt 0) {
        $successRate = [math]::Round(($passedTests * 100 / $totalTests), 2)
    }
    
    # Return results as PSObject
    return [PSCustomObject]@{
        total = $totalTests
        passed = $passedTests
        failed = $failedTests
        success_rate = $successRate
    }
}

# Run all tests and collect results
Write-Host "Running all tests and collecting results..." -ForegroundColor Cyan

# Run individual service tests
$authResults = Run-TestsAndCapture -Service "auth"
$strategyResults = Run-TestsAndCapture -Service "strategy"
$backtestResults = Run-TestsAndCapture -Service "backtest"
$tradeResults = Run-TestsAndCapture -Service "trade"
$dataResults = Run-TestsAndCapture -Service "data"

# Run integration tests
$integrationResults = Run-IntegrationTests

# Run performance tests
$performanceResults = Run-PerformanceTests

# Create JSON report
Write-Host "Creating JSON report..." -ForegroundColor Cyan
$jsonReport = [PSCustomObject]@{
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    individual_services = [PSCustomObject]@{
        auth = $authResults
        strategy = $strategyResults
        backtest = $backtestResults
        trade = $tradeResults
        data = $dataResults
    }
    integration = $integrationResults
    performance = $performanceResults
}

$jsonReport | ConvertTo-Json -Depth 5 | Out-File -FilePath $jsonReportFile -Encoding utf8

# Create markdown report
Write-Host "Creating markdown report..." -ForegroundColor Cyan

# Function to get detailed test results
function Get-DetailedTestResults {
    param (
        [string]$OutputFile
    )
    
    if (Test-Path -Path $OutputFile) {
        $content = Get-Content -Path $OutputFile
        $results = $content | Where-Object { $_ -match "PASSED|FAILED|SKIPPED" } | ForEach-Object { "- $_" }
        return $results -join "`n"
    }
    
    return "- No test results found"
}

# Function to get integration test results
function Get-IntegrationTestResults {
    param (
        [string]$OutputFile
    )
    
    if (Test-Path -Path $OutputFile) {
        $content = Get-Content -Path $OutputFile
        $results = $content | Where-Object { $_ -match "Successfully|Failed" } | ForEach-Object { "- $_" }
        return $results -join "`n"
    }
    
    return "- No test results found"
}

# Generate recommendations based on test results
$recommendations = @()

if ($authResults.success_rate -lt 90) { $recommendations += "- Auth service needs improvement" }
if ($strategyResults.success_rate -lt 90) { $recommendations += "- Strategy service needs improvement" }
if ($backtestResults.success_rate -lt 90) { $recommendations += "- Backtest service needs improvement" }
if ($tradeResults.success_rate -lt 90) { $recommendations += "- Trade service needs improvement" }
if ($dataResults.success_rate -lt 90) { $recommendations += "- Data service needs improvement" }
if ($integrationResults.success_rate -lt 90) { $recommendations += "- Integration between services needs improvement" }

if ($performanceResults.auth_rps -lt 10) { $recommendations += "- Auth service performance needs optimization" }
if ($performanceResults.data_rps -lt 10) { $recommendations += "- Data service performance needs optimization" }
if ($performanceResults.strategy_rps -lt 5) { $recommendations += "- Strategy service performance needs optimization" }
if ($performanceResults.trade_rps -lt 5) { $recommendations += "- Trade service performance needs optimization" }
if ($performanceResults.backtest_rps -lt 1) { $recommendations += "- Backtest service performance needs optimization" }

if ($recommendations.Count -eq 0) {
    $recommendations += "- All services are performing well"
}

$markdownReport = @"
# Cryptobot Test Report

**Generated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") UTC

## Summary

| Service | Total Tests | Passed | Failed | Success Rate |
|---------|------------|--------|--------|-------------|
| Auth | $($authResults.total) | $($authResults.passed) | $($authResults.failed) | $($authResults.success_rate)% |
| Strategy | $($strategyResults.total) | $($strategyResults.passed) | $($strategyResults.failed) | $($strategyResults.success_rate)% |
| Backtest | $($backtestResults.total) | $($backtestResults.passed) | $($backtestResults.failed) | $($backtestResults.success_rate)% |
| Trade | $($tradeResults.total) | $($tradeResults.passed) | $($tradeResults.failed) | $($tradeResults.success_rate)% |
| Data | $($dataResults.total) | $($dataResults.passed) | $($dataResults.failed) | $($dataResults.success_rate)% |
| Integration | $($integrationResults.total) | $($integrationResults.passed) | $($integrationResults.failed) | $($integrationResults.success_rate)% |

## Performance Metrics

| Service | Requests/Second |
|---------|----------------|
| Auth | $($performanceResults.auth_rps) |
| Data | $($performanceResults.data_rps) |
| Strategy | $($performanceResults.strategy_rps) |
| Trade | $($performanceResults.trade_rps) |
| Backtest | $($performanceResults.backtest_rps) |

## Detailed Results

### Auth Service
$(Get-DetailedTestResults -OutputFile "$reportDir\auth_test_output.txt")

### Strategy Service
$(Get-DetailedTestResults -OutputFile "$reportDir\strategy_test_output.txt")

### Backtest Service
$(Get-DetailedTestResults -OutputFile "$reportDir\backtest_test_output.txt")

### Trade Service
$(Get-DetailedTestResults -OutputFile "$reportDir\trade_test_output.txt")

### Data Service
$(Get-DetailedTestResults -OutputFile "$reportDir\data_test_output.txt")

### Integration Tests
$(Get-IntegrationTestResults -OutputFile "$reportDir\integration_test_output.txt")

## Recommendations

$($recommendations -join "`n")
"@

$markdownReport | Out-File -FilePath $reportFile -Encoding utf8

# Convert markdown to HTML if pandoc is available
Write-Host "Converting markdown to HTML..." -ForegroundColor Cyan
try {
    if (Get-Command pandoc -ErrorAction SilentlyContinue) {
        pandoc -f markdown -t html $reportFile -o $htmlReportFile
        Write-Host "HTML report generated: $htmlReportFile" -ForegroundColor Green
    } else {
        Write-Host "Pandoc not found. Skipping HTML report generation." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Error converting markdown to HTML: $_" -ForegroundColor Red
}

Write-Host "Test reports generated:" -ForegroundColor Green
Write-Host "- Markdown: $reportFile" -ForegroundColor Green
Write-Host "- JSON: $jsonReportFile" -ForegroundColor Green

Write-Host "===== Test Result Report Generation Complete =====" -ForegroundColor Cyan