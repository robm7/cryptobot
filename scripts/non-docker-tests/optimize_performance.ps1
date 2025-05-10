# Performance Optimization Script (PowerShell)
# Analyzes system performance and suggests optimizations

# Set environment variables
$env:PYTHONPATH = (Get-Location).Path

Write-Host "===== Performance Optimization =====" -ForegroundColor Cyan
Write-Host "Analyzing system performance and suggesting optimizations..." -ForegroundColor Cyan

# Create output directory for reports
$reportDir = "optimization_reports"
if (-not (Test-Path -Path $reportDir)) {
    New-Item -Path $reportDir -ItemType Directory | Out-Null
}

# Get current timestamp for report filenames
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$reportFile = "$reportDir\optimization_report_$timestamp.md"
$htmlReportFile = "$reportDir\optimization_report_$timestamp.html"

# Function to check system resources
function Check-SystemResources {
    Write-Host "Checking system resources..." -ForegroundColor Cyan
    
    # CPU info
    $cpuInfo = Get-WmiObject -Class Win32_Processor | Select-Object -First 1 -ExpandProperty Name
    $cpuCores = (Get-WmiObject -Class Win32_Processor | Measure-Object -Property NumberOfCores -Sum).Sum
    $cpuUsage = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 1).CounterSamples[0].CookedValue
    
    # Memory info
    $computerSystem = Get-WmiObject -Class Win32_ComputerSystem
    $totalMemory = [math]::Round($computerSystem.TotalPhysicalMemory / 1MB)
    $osInfo = Get-WmiObject -Class Win32_OperatingSystem
    $usedMemory = [math]::Round(($totalMemory - ($osInfo.FreePhysicalMemory / 1KB)))
    $memoryUsage = [math]::Round(($usedMemory / $totalMemory) * 100, 2)
    
    # Disk info
    $diskUsage = (Get-WmiObject -Class Win32_LogicalDisk | Where-Object { $_.DriveType -eq 3 } | Select-Object -First 1 | ForEach-Object { [math]::Round((1 - ($_.FreeSpace / $_.Size)) * 100, 2) })
    
    # Network info
    $networkConnections = (Get-NetTCPConnection -State Established).Count
    
    Write-Host "CPU: $cpuInfo ($cpuCores cores, $([math]::Round($cpuUsage, 2))% usage)" -ForegroundColor Green
    Write-Host "Memory: $usedMemory MB / $totalMemory MB ($memoryUsage% usage)" -ForegroundColor Green
    Write-Host "Disk: $diskUsage% usage" -ForegroundColor Green
    Write-Host "Network: $networkConnections established connections" -ForegroundColor Green
    
    # Return results as PSObject
    return [PSCustomObject]@{
        cpu = [PSCustomObject]@{
            model = $cpuInfo
            cores = $cpuCores
            usage = $cpuUsage
        }
        memory = [PSCustomObject]@{
            total = $totalMemory
            used = $usedMemory
            usage = $memoryUsage
        }
        disk = [PSCustomObject]@{
            usage = $diskUsage
        }
        network = [PSCustomObject]@{
            connections = $networkConnections
        }
    }
}

# Function to check database performance
function Check-DatabasePerformance {
    Write-Host "Checking database performance..." -ForegroundColor Cyan
    
    # Run database performance tests
    $dbPerformanceScript = @"
import time
import sqlite3
from database.session import get_session
from sqlalchemy import text

# Test SQLAlchemy ORM performance
start_time = time.time()
session = get_session()
result = session.execute(text('SELECT 1'))
session.close()
orm_time = time.time() - start_time

# Test raw SQLite performance
start_time = time.time()
conn = sqlite3.connect('instance/cryptobot.db')
cursor = conn.cursor()
cursor.execute('SELECT 1')
conn.close()
raw_time = time.time() - start_time

# Print results
print(f'ORM query time: {orm_time:.6f} seconds')
print(f'Raw query time: {raw_time:.6f} seconds')
print(f'ORM overhead: {(orm_time/raw_time):.2f}x')
"@
    
    $dbPerformanceOutput = "$reportDir\db_performance.txt"
    $dbPerformanceScript | Out-File -FilePath "$env:TEMP\db_performance_test.py" -Encoding utf8
    python "$env:TEMP\db_performance_test.py" > $dbPerformanceOutput
    
    # Extract results
    $dbPerformanceContent = Get-Content -Path $dbPerformanceOutput -Raw
    
    $ormTime = 0
    if ($dbPerformanceContent -match "ORM query time: (\d+\.\d+) seconds") {
        $ormTime = [double]$Matches[1]
    }
    
    $rawTime = 0
    if ($dbPerformanceContent -match "Raw query time: (\d+\.\d+) seconds") {
        $rawTime = [double]$Matches[1]
    }
    
    $ormOverhead = 0
    if ($dbPerformanceContent -match "ORM overhead: (\d+\.\d+)x") {
        $ormOverhead = [double]$Matches[1]
    }
    
    Write-Host "ORM query time: $ormTime seconds" -ForegroundColor Green
    Write-Host "Raw query time: $rawTime seconds" -ForegroundColor Green
    Write-Host "ORM overhead: $ormOverhead" -ForegroundColor Green
    
    # Return results as PSObject
    return [PSCustomObject]@{
        orm_time = $ormTime
        raw_time = $rawTime
        orm_overhead = $ormOverhead
    }
}

# Function to check API endpoint performance
function Check-ApiPerformance {
    Write-Host "Checking API endpoint performance..." -ForegroundColor Cyan
    
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
            return $null
        }
    } catch {
        Write-Host "Failed to get access token: $_" -ForegroundColor Red
        return $null
    }
    
    # Test endpoints
    $endpoints = @(
        "auth/protected"
        "strategy"
        "backtest"
        "trade"
        "data/historical?symbol=BTCUSDT&timeframe=1h&limit=10"
    )
    
    Write-Host "Testing API endpoint performance..." -ForegroundColor Cyan
    $apiPerformanceOutput = "$reportDir\api_performance.csv"
    "Endpoint,Response Time (ms)" | Out-File -FilePath $apiPerformanceOutput -Encoding utf8
    
    $endpointResults = @()
    
    foreach ($endpoint in $endpoints) {
        Write-Host "Testing $endpoint..." -ForegroundColor Cyan
        $startTime = Get-Date
        
        try {
            Invoke-RestMethod -Uri "http://localhost:8000/$endpoint" -Method Get -Headers @{Authorization = "Bearer $token"} -ErrorAction SilentlyContinue | Out-Null
        } catch {
            # Ignore errors during performance testing
        }
        
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalMilliseconds
        
        "$endpoint,$duration" | Out-File -FilePath $apiPerformanceOutput -Encoding utf8 -Append
        Write-Host "$endpoint: $([math]::Round($duration, 2)) ms" -ForegroundColor Green
        
        $endpointResults += [PSCustomObject]@{
            endpoint = $endpoint
            time = $duration
        }
    }
    
    # Calculate average response time
    $averageTime = ($endpointResults | Measure-Object -Property time -Average).Average
    Write-Host "Average response time: $([math]::Round($averageTime, 2)) ms" -ForegroundColor Green
    
    # Find slowest endpoint
    $slowestEndpoint = $endpointResults | Sort-Object -Property time -Descending | Select-Object -First 1
    Write-Host "Slowest endpoint: $($slowestEndpoint.endpoint) ($([math]::Round($slowestEndpoint.time, 2)) ms)" -ForegroundColor Green
    
    # Return results as PSObject
    return [PSCustomObject]@{
        average_time = $averageTime
        slowest_endpoint = $slowestEndpoint.endpoint
        slowest_time = $slowestEndpoint.time
        endpoints = $endpointResults
    }
}

# Function to check service resource usage
function Check-ServiceResourceUsage {
    Write-Host "Checking service resource usage..." -ForegroundColor Cyan
    
    # Get process IDs for each service
    $authProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*auth/main.py*" } | Select-Object -First 1
    $strategyProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*strategy/main.py*" } | Select-Object -First 1
    $backtestProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*backtest/main.py*" } | Select-Object -First 1
    $tradeProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*trade/main.py*" } | Select-Object -First 1
    $dataProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*data/main.py*" } | Select-Object -First 1
    
    # Check CPU and memory usage for each service
    $serviceResourceOutput = "$reportDir\service_resource_usage.csv"
    "Service,PID,CPU %,Memory %" | Out-File -FilePath $serviceResourceOutput -Encoding utf8
    
    $serviceResults = @()
    
    if ($authProcess) {
        $authCpu = $authProcess.CPU
        $authMem = [math]::Round(($authProcess.WorkingSet / (Get-WmiObject -Class Win32_ComputerSystem).TotalPhysicalMemory) * 100, 2)
        "Auth,$($authProcess.Id),$authCpu,$authMem" | Out-File -FilePath $serviceResourceOutput -Encoding utf8 -Append
        Write-Host "Auth service: $authCpu% CPU, $authMem% memory" -ForegroundColor Green
        
        $serviceResults += [PSCustomObject]@{
            service = "Auth"
            pid = $authProcess.Id
            cpu = $authCpu
            memory = $authMem
        }
    }
    
    if ($strategyProcess) {
        $strategyCpu = $strategyProcess.CPU
        $strategyMem = [math]::Round(($strategyProcess.WorkingSet / (Get-WmiObject -Class Win32_ComputerSystem).TotalPhysicalMemory) * 100, 2)
        "Strategy,$($strategyProcess.Id),$strategyCpu,$strategyMem" | Out-File -FilePath $serviceResourceOutput -Encoding utf8 -Append
        Write-Host "Strategy service: $strategyCpu% CPU, $strategyMem% memory" -ForegroundColor Green
        
        $serviceResults += [PSCustomObject]@{
            service = "Strategy"
            pid = $strategyProcess.Id
            cpu = $strategyCpu
            memory = $strategyMem
        }
    }
    
    if ($backtestProcess) {
        $backtestCpu = $backtestProcess.CPU
        $backtestMem = [math]::Round(($backtestProcess.WorkingSet / (Get-WmiObject -Class Win32_ComputerSystem).TotalPhysicalMemory) * 100, 2)
        "Backtest,$($backtestProcess.Id),$backtestCpu,$backtestMem" | Out-File -FilePath $serviceResourceOutput -Encoding utf8 -Append
        Write-Host "Backtest service: $backtestCpu% CPU, $backtestMem% memory" -ForegroundColor Green
        
        $serviceResults += [PSCustomObject]@{
            service = "Backtest"
            pid = $backtestProcess.Id
            cpu = $backtestCpu
            memory = $backtestMem
        }
    }
    
    if ($tradeProcess) {
        $tradeCpu = $tradeProcess.CPU
        $tradeMem = [math]::Round(($tradeProcess.WorkingSet / (Get-WmiObject -Class Win32_ComputerSystem).TotalPhysicalMemory) * 100, 2)
        "Trade,$($tradeProcess.Id),$tradeCpu,$tradeMem" | Out-File -FilePath $serviceResourceOutput -Encoding utf8 -Append
        Write-Host "Trade service: $tradeCpu% CPU, $tradeMem% memory" -ForegroundColor Green
        
        $serviceResults += [PSCustomObject]@{
            service = "Trade"
            pid = $tradeProcess.Id
            cpu = $tradeCpu
            memory = $tradeMem
        }
    }
    
    if ($dataProcess) {
        $dataCpu = $dataProcess.CPU
        $dataMem = [math]::Round(($dataProcess.WorkingSet / (Get-WmiObject -Class Win32_ComputerSystem).TotalPhysicalMemory) * 100, 2)
        "Data,$($dataProcess.Id),$dataCpu,$dataMem" | Out-File -FilePath $serviceResourceOutput -Encoding utf8 -Append
        Write-Host "Data service: $dataCpu% CPU, $dataMem% memory" -ForegroundColor Green
        
        $serviceResults += [PSCustomObject]@{
            service = "Data"
            pid = $dataProcess.Id
            cpu = $dataCpu
            memory = $dataMem
        }
    }
    
    # Find service with highest CPU and memory usage
    $highestCpuService = $serviceResults | Sort-Object -Property cpu -Descending | Select-Object -First 1
    $highestMemService = $serviceResults | Sort-Object -Property memory -Descending | Select-Object -First 1
    
    if ($highestCpuService) {
        Write-Host "Service with highest CPU usage: $($highestCpuService.service) ($($highestCpuService.cpu)%)" -ForegroundColor Green
    }
    
    if ($highestMemService) {
        Write-Host "Service with highest memory usage: $($highestMemService.service) ($($highestMemService.memory)%)" -ForegroundColor Green
    }
    
    # Return results as PSObject
    return [PSCustomObject]@{
        highest_cpu = [PSCustomObject]@{
            service = if ($highestCpuService) { $highestCpuService.service } else { "None" }
            usage = if ($highestCpuService) { $highestCpuService.cpu } else { 0 }
        }
        highest_memory = [PSCustomObject]@{
            service = if ($highestMemService) { $highestMemService.service } else { "None" }
            usage = if ($highestMemService) { $highestMemService.memory } else { 0 }
        }
        services = $serviceResults
    }
}

# Function to generate optimization recommendations
function Generate-Recommendations {
    param (
        [PSCustomObject]$SystemResources,
        [PSCustomObject]$DbPerformance,
        [PSCustomObject]$ApiPerformance,
        [PSCustomObject]$ServiceUsage
    )
    
    Write-Host "Generating optimization recommendations..." -ForegroundColor Cyan
    
    # System resources
    $cpuUsage = $SystemResources.cpu.usage
    $memUsage = $SystemResources.memory.usage
    $diskUsage = $SystemResources.disk.usage
    
    # Database performance
    $ormOverhead = $DbPerformance.orm_overhead
    
    # API performance
    $slowestEndpoint = $ApiPerformance.slowest_endpoint
    $slowestTime = $ApiPerformance.slowest_time
    
    # Service resource usage
    $highestCpuService = $ServiceUsage.highest_cpu.service
    $highestCpu = $ServiceUsage.highest_cpu.usage
    $highestMemService = $ServiceUsage.highest_memory.service
    $highestMem = $ServiceUsage.highest_memory.usage
    
    # Generate recommendations
    $recommendations = @()
    
    # System resource recommendations
    if ($cpuUsage -gt 80) {
        $recommendations += "- **High CPU Usage**: Consider upgrading CPU or optimizing CPU-intensive operations."
    }
    
    if ($memUsage -gt 80) {
        $recommendations += "- **High Memory Usage**: Consider adding more RAM or optimizing memory-intensive operations."
    }
    
    if ($diskUsage -gt 80) {
        $recommendations += "- **High Disk Usage**: Consider adding more storage or cleaning up unnecessary files."
    }
    
    # Database recommendations
    if ($ormOverhead -gt 2) {
        $recommendations += "- **High ORM Overhead**: Consider using raw SQL queries for performance-critical operations."
    }
    
    # API recommendations
    if ($slowestTime -gt 500) {
        $recommendations += "- **Slow API Endpoint**: Optimize the '$slowestEndpoint' endpoint ($([math]::Round($slowestTime, 2)) ms)."
    }
    
    # Service recommendations
    if ($highestCpu -gt 50) {
        $recommendations += "- **High CPU Service**: Optimize the $highestCpuService service ($([math]::Round($highestCpu, 2))% CPU)."
    }
    
    if ($highestMem -gt 50) {
        $recommendations += "- **High Memory Service**: Optimize the $highestMemService service ($([math]::Round($highestMem, 2))% memory)."
    }
    
    # General recommendations
    $recommendations += @(
        "- **Database Indexing**: Ensure proper indexes are created for frequently queried fields."
        "- **Connection Pooling**: Implement connection pooling for database connections."
        "- **Caching**: Implement caching for frequently accessed data."
        "- **Asynchronous Processing**: Use asynchronous processing for non-critical operations."
        "- **Load Balancing**: Consider implementing load balancing for high-traffic services."
    )
    
    return $recommendations
}

# Run all checks and collect results
Write-Host "Running all checks and collecting results..." -ForegroundColor Cyan

# Check system resources
Write-Host "Checking system resources..." -ForegroundColor Cyan
$systemResources = Check-SystemResources

# Check database performance
Write-Host "Checking database performance..." -ForegroundColor Cyan
$dbPerformance = Check-DatabasePerformance

# Check API performance
Write-Host "Checking API performance..." -ForegroundColor Cyan
$apiPerformance = Check-ApiPerformance

# Check service resource usage
Write-Host "Checking service resource usage..." -ForegroundColor Cyan
$serviceUsage = Check-ServiceResourceUsage

# Generate recommendations
Write-Host "Generating recommendations..." -ForegroundColor Cyan
$recommendations = Generate-Recommendations -SystemResources $systemResources -DbPerformance $dbPerformance -ApiPerformance $apiPerformance -ServiceUsage $serviceUsage

# Create optimization report
Write-Host "Creating optimization report..." -ForegroundColor Cyan

$endpointTable = $apiPerformance.endpoints | ForEach-Object {
    "| $($_.endpoint) | $([math]::Round($_.time, 2)) |"
} | Out-String

$serviceTable = $serviceUsage.services | ForEach-Object {
    "| $($_.service) | $([math]::Round($_.cpu, 2)) | $([math]::Round($_.memory, 2)) |"
} | Out-String

$markdownReport = @"
# Cryptobot Performance Optimization Report

**Generated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") UTC

## System Resources

- **CPU:** $($systemResources.cpu.model) ($($systemResources.cpu.cores) cores)
- **CPU Usage:** $([math]::Round($systemResources.cpu.usage, 2))%
- **Memory:** $($systemResources.memory.used) MB / $($systemResources.memory.total) MB
- **Memory Usage:** $([math]::Round($systemResources.memory.usage, 2))%
- **Disk Usage:** $([math]::Round($systemResources.disk.usage, 2))%
- **Network Connections:** $($systemResources.network.connections)

## Database Performance

- **ORM Query Time:** $([math]::Round($dbPerformance.orm_time, 6)) seconds
- **Raw Query Time:** $([math]::Round($dbPerformance.raw_time, 6)) seconds
- **ORM Overhead:** $([math]::Round($dbPerformance.orm_overhead, 2))x

## API Performance

- **Average Response Time:** $([math]::Round($apiPerformance.average_time, 2)) ms
- **Slowest Endpoint:** $($apiPerformance.slowest_endpoint) ($([math]::Round($apiPerformance.slowest_time, 2)) ms)

### Endpoint Response Times

| Endpoint | Response Time (ms) |
|----------|-------------------|
$endpointTable

## Service Resource Usage

| Service | CPU % | Memory % |
|---------|-------|----------|
$serviceTable

- **Highest CPU Usage:** $($serviceUsage.highest_cpu.service) ($([math]::Round($serviceUsage.highest_cpu.usage, 2))%)
- **Highest Memory Usage:** $($serviceUsage.highest_memory.service) ($([math]::Round($serviceUsage.highest_memory.usage, 2))%)

## Optimization Recommendations

$($recommendations -join "`n")

## Implementation Plan

1. **Short-term Optimizations:**
   - Implement caching for frequently accessed data
   - Add database indexes for common queries
   - Optimize the slowest API endpoint

2. **Medium-term Optimizations:**
   - Implement connection pooling
   - Optimize high CPU/memory services
   - Add asynchronous processing for non-critical operations

3. **Long-term Optimizations:**
   - Consider scaling horizontally with load balancing
   - Evaluate database sharding for improved performance
   - Implement microservices architecture for better scalability
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

Write-Host "Optimization reports generated:" -ForegroundColor Green
Write-Host "- Markdown: $reportFile" -ForegroundColor Green
if (Test-Path $htmlReportFile) {
    Write-Host "- HTML: $htmlReportFile" -ForegroundColor Green
}

Write-Host "===== Performance Optimization Complete =====" -ForegroundColor Cyan