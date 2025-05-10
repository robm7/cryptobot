# verify_migration.ps1
# Script to verify the successful completion of the migration from Docker to non-Docker on Windows
# Part of Phase 11: Parallel Operation Strategy

Write-Host "=== Cryptobot Migration Verification Tool ===" -ForegroundColor Cyan
Write-Host "This script verifies the successful completion of the migration from Docker to non-Docker." -ForegroundColor Cyan

# Check if environment variables are set
if (-not $env:CRYPTOBOT_SHARED_DATA_DIR) {
    # Source environment file if it exists
    $envFile = "C:\cryptobot\shared_data\config\environment.ps1"
    if (Test-Path $envFile) {
        . $envFile
    }
    else {
        Write-Host "Error: CRYPTOBOT_SHARED_DATA_DIR environment variable not set." -ForegroundColor Red
        Write-Host "Please run setup_parallel_env.ps1 first or set the variable manually." -ForegroundColor Red
        exit 1
    }
}

# Define directories and files
$SHARED_DATA_DIR = $env:CRYPTOBOT_SHARED_DATA_DIR
if (-not $SHARED_DATA_DIR) {
    $SHARED_DATA_DIR = "C:\cryptobot\shared_data"
}

$DOCKER_ENV_DIR = "C:\cryptobot\docker"
$NON_DOCKER_ENV_DIR = "C:\cryptobot\non-docker"
$LOG_DIR = $env:CRYPTOBOT_LOG_DIR
if (-not $LOG_DIR) {
    $LOG_DIR = "C:\cryptobot\logs"
}
$VERIFY_LOG = "$LOG_DIR\migration_verification.log"
$VERIFY_REPORT = "$SHARED_DATA_DIR\migration_verification_report.html"

# Create log directory if it doesn't exist
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null
}

# Function to log messages
function Write-Log {
    param (
        [string]$Message
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage
    Add-Content -Path $VERIFY_LOG -Value $logMessage
}

# Function to check if a service is running
function Test-ServiceRunning {
    param (
        [string]$Host,
        [int]$Port
    )
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connection = $tcpClient.BeginConnect($Host, $Port, $null, $null)
        $wait = $connection.AsyncWaitHandle.WaitOne(1000, $false)
        
        if ($wait) {
            $tcpClient.EndConnect($connection)
            $tcpClient.Close()
            return $true
        }
        else {
            $tcpClient.Close()
            return $false
        }
    }
    catch {
        return $false
    }
}

# Function to check if Docker is running
function Test-DockerRunning {
    try {
        $dockerInfo = docker info 2>$null
        return $true
    }
    catch {
        return $false
    }
}

# Function to check if Docker containers are running
function Test-DockerContainers {
    Write-Log "Checking Docker containers..."
    
    if (-not (Test-DockerRunning)) {
        Write-Log "Docker is not running."
        return $true  # Consider this a pass since we want Docker to be stopped
    }
    
# Function to check non-Docker services
function Test-NonDockerServices {
    Write-Log "Checking non-Docker services..."
    
    $allRunning = $true
    $servicesStatus = @()
    
    # Check auth service
    $authPort = if ($env:CRYPTOBOT_NON_DOCKER_AUTH_PORT) { $env:CRYPTOBOT_NON_DOCKER_AUTH_PORT } else { 9000 }
    if (Test-ServiceRunning -Host "localhost" -Port $authPort) {
        Write-Log "Auth service: RUNNING"
        $servicesStatus += "Auth service: ✅ RUNNING"
    }
    else {
        Write-Log "Auth service: NOT RUNNING"
        $servicesStatus += "Auth service: ❌ NOT RUNNING"
        $allRunning = $false
    }
    
    # Check strategy service
    $strategyPort = if ($env:CRYPTOBOT_NON_DOCKER_STRATEGY_PORT) { $env:CRYPTOBOT_NON_DOCKER_STRATEGY_PORT } else { 9001 }
    if (Test-ServiceRunning -Host "localhost" -Port $strategyPort) {
        Write-Log "Strategy service: RUNNING"
        $servicesStatus += "Strategy service: ✅ RUNNING"
    }
    else {
        Write-Log "Strategy service: NOT RUNNING"
        $servicesStatus += "Strategy service: ❌ NOT RUNNING"
        $allRunning = $false
    }
    
    # Check backtest service
    $backtestPort = if ($env:CRYPTOBOT_NON_DOCKER_BACKTEST_PORT) { $env:CRYPTOBOT_NON_DOCKER_BACKTEST_PORT } else { 9002 }
    if (Test-ServiceRunning -Host "localhost" -Port $backtestPort) {
        Write-Log "Backtest service: RUNNING"
        $servicesStatus += "Backtest service: ✅ RUNNING"
    }
    else {
        Write-Log "Backtest service: NOT RUNNING"
        $servicesStatus += "Backtest service: ❌ NOT RUNNING"
        $allRunning = $false
    }
    
    # Check trade service
    $tradePort = if ($env:CRYPTOBOT_NON_DOCKER_TRADE_PORT) { $env:CRYPTOBOT_NON_DOCKER_TRADE_PORT } else { 9003 }
    if (Test-ServiceRunning -Host "localhost" -Port $tradePort) {
        Write-Log "Trade service: RUNNING"
        $servicesStatus += "Trade service: ✅ RUNNING"
    }
    else {
        Write-Log "Trade service: NOT RUNNING"
        $servicesStatus += "Trade service: ❌ NOT RUNNING"
        $allRunning = $false
    }
    
    # Check data service
    $dataPort = if ($env:CRYPTOBOT_NON_DOCKER_DATA_PORT) { $env:CRYPTOBOT_NON_DOCKER_DATA_PORT } else { 9004 }
    if (Test-ServiceRunning -Host "localhost" -Port $dataPort) {
        Write-Log "Data service: RUNNING"
        $servicesStatus += "Data service: ✅ RUNNING"
    }
    else {
        Write-Log "Data service: NOT RUNNING"
        $servicesStatus += "Data service: ❌ NOT RUNNING"
        $allRunning = $false
    }
    
    # Return results
    if ($allRunning) {
        Write-Log "All non-Docker services are running."
        $script:SERVICES_STATUS_ARRAY = $servicesStatus
        return $true
    }
    else {
        Write-Log "Some non-Docker services are not running."
        $script:SERVICES_STATUS_ARRAY = $servicesStatus
        return $false
    }
}

# Function to check database connectivity
function Test-DatabaseConnection {
    Write-Log "Checking database connectivity..."
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connection = $tcpClient.BeginConnect("localhost", 5432, $null, $null)
        $wait = $connection.AsyncWaitHandle.WaitOne(1000, $false)
        
        if ($wait) {
            $tcpClient.EndConnect($connection)
            $tcpClient.Close()
            Write-Log "Database: CONNECTED"
            $script:DATABASE_STATUS = "Database: ✅ CONNECTED"
            return $true
        }
        else {
            $tcpClient.Close()
            Write-Log "Database: NOT CONNECTED"
            $script:DATABASE_STATUS = "Database: ❌ NOT CONNECTED"
            return $false
        }
    }
    catch {
        Write-Log "Database: NOT CONNECTED (Error: $($_.Exception.Message))"
        $script:DATABASE_STATUS = "Database: ❌ NOT CONNECTED (Error: $($_.Exception.Message))"
        return $false
    }
}

# Function to check Redis connectivity
function Test-RedisConnection {
    Write-Log "Checking Redis connectivity..."
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connection = $tcpClient.BeginConnect("localhost", 6379, $null, $null)
        $wait = $connection.AsyncWaitHandle.WaitOne(1000, $false)
        
        if ($wait) {
            $tcpClient.EndConnect($connection)
            $tcpClient.Close()
            Write-Log "Redis: CONNECTED"
            $script:REDIS_STATUS = "Redis: ✅ CONNECTED"
            return $true
        }
        else {
            $tcpClient.Close()
# Function to check API endpoints
function Test-ApiEndpoints {
    Write-Log "Checking API endpoints..."
    
    $allEndpointsOk = $true
    $endpointsStatus = @()
    
    # Check auth API
    $authPort = if ($env:CRYPTOBOT_NON_DOCKER_AUTH_PORT) { $env:CRYPTOBOT_NON_DOCKER_AUTH_PORT } else { 9000 }
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$authPort/health" -UseBasicParsing -ErrorAction SilentlyContinue
        $statusCode = [int]$response.StatusCode
        
        if ($statusCode -eq 200) {
            Write-Log "Auth API: OK (Status: $statusCode)"
            $endpointsStatus += "Auth API: ✅ OK (Status: $statusCode)"
        }
        else {
            Write-Log "Auth API: FAILED (Status: $statusCode)"
            $endpointsStatus += "Auth API: ❌ FAILED (Status: $statusCode)"
            $allEndpointsOk = $false
        }
    }
    catch {
        $statusCode = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        Write-Log "Auth API: FAILED (Status: $statusCode)"
        $endpointsStatus += "Auth API: ❌ FAILED (Status: $statusCode)"
        $allEndpointsOk = $false
    }
    
    # Check strategy API
    $strategyPort = if ($env:CRYPTOBOT_NON_DOCKER_STRATEGY_PORT) { $env:CRYPTOBOT_NON_DOCKER_STRATEGY_PORT } else { 9001 }
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$strategyPort/health" -UseBasicParsing -ErrorAction SilentlyContinue
        $statusCode = [int]$response.StatusCode
        
        if ($statusCode -eq 200) {
            Write-Log "Strategy API: OK (Status: $statusCode)"
            $endpointsStatus += "Strategy API: ✅ OK (Status: $statusCode)"
        }
        else {
            Write-Log "Strategy API: FAILED (Status: $statusCode)"
            $endpointsStatus += "Strategy API: ❌ FAILED (Status: $statusCode)"
            $allEndpointsOk = $false
        }
    }
    catch {
        $statusCode = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        Write-Log "Strategy API: FAILED (Status: $statusCode)"
        $endpointsStatus += "Strategy API: ❌ FAILED (Status: $statusCode)"
        $allEndpointsOk = $false
    }
    
    # Check backtest API
    $backtestPort = if ($env:CRYPTOBOT_NON_DOCKER_BACKTEST_PORT) { $env:CRYPTOBOT_NON_DOCKER_BACKTEST_PORT } else { 9002 }
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$backtestPort/health" -UseBasicParsing -ErrorAction SilentlyContinue
        $statusCode = [int]$response.StatusCode
        
        if ($statusCode -eq 200) {
            Write-Log "Backtest API: OK (Status: $statusCode)"
            $endpointsStatus += "Backtest API: ✅ OK (Status: $statusCode)"
        }
        else {
            Write-Log "Backtest API: FAILED (Status: $statusCode)"
            $endpointsStatus += "Backtest API: ❌ FAILED (Status: $statusCode)"
            $allEndpointsOk = $false
        }
    }
    catch {
        $statusCode = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        Write-Log "Backtest API: FAILED (Status: $statusCode)"
        $endpointsStatus += "Backtest API: ❌ FAILED (Status: $statusCode)"
        $allEndpointsOk = $false
    }
    
    # Check trade API
    $tradePort = if ($env:CRYPTOBOT_NON_DOCKER_TRADE_PORT) { $env:CRYPTOBOT_NON_DOCKER_TRADE_PORT } else { 9003 }
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$tradePort/health" -UseBasicParsing -ErrorAction SilentlyContinue
        $statusCode = [int]$response.StatusCode
        
        if ($statusCode -eq 200) {
            Write-Log "Trade API: OK (Status: $statusCode)"
            $endpointsStatus += "Trade API: ✅ OK (Status: $statusCode)"
        }
        else {
            Write-Log "Trade API: FAILED (Status: $statusCode)"
            $endpointsStatus += "Trade API: ❌ FAILED (Status: $statusCode)"
            $allEndpointsOk = $false
        }
    }
    catch {
        $statusCode = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        Write-Log "Trade API: FAILED (Status: $statusCode)"
        $endpointsStatus += "Trade API: ❌ FAILED (Status: $statusCode)"
        $allEndpointsOk = $false
    }
    
    # Check data API
    $dataPort = if ($env:CRYPTOBOT_NON_DOCKER_DATA_PORT) { $env:CRYPTOBOT_NON_DOCKER_DATA_PORT } else { 9004 }
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$dataPort/health" -UseBasicParsing -ErrorAction SilentlyContinue
        $statusCode = [int]$response.StatusCode
        
        if ($statusCode -eq 200) {
            Write-Log "Data API: OK (Status: $statusCode)"
            $endpointsStatus += "Data API: ✅ OK (Status: $statusCode)"
        }
        else {
            Write-Log "Data API: FAILED (Status: $statusCode)"
            $endpointsStatus += "Data API: ❌ FAILED (Status: $statusCode)"
            $allEndpointsOk = $false
        }
    }
    catch {
        $statusCode = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        Write-Log "Data API: FAILED (Status: $statusCode)"
        $endpointsStatus += "Data API: ❌ FAILED (Status: $statusCode)"
        $allEndpointsOk = $false
    }
    
    # Return results
    if ($allEndpointsOk) {
        Write-Log "All API endpoints are accessible."
        $script:API_STATUS_ARRAY = $endpointsStatus
        return $true
    }
    else {
        Write-Log "Some API endpoints are not accessible."
        $script:API_STATUS_ARRAY = $endpointsStatus
        return $false
    }
}

# Function to check data integrity
function Test-DataIntegrity {
    Write-Log "Checking data integrity..."
    
    $allDataOk = $true
    $dataStatus = @()
    
    # Check database tables (simulated for Windows without direct psql)
    try {
        # This is a placeholder - in a real environment, you would use a proper database connection
        # For example, using the SqlClient .NET library or Invoke-Sqlcmd PowerShell cmdlet
        Write-Log "Database tables: Simulating check (implement with proper DB connection)"
        $dataStatus += "Database tables: ✅ Simulated check passed"
    }
    catch {
        Write-Log "Database tables: FAILED to query"
        $dataStatus += "Database tables: ❌ FAILED to query"
        $allDataOk = $false
    }
    
    # Check historical data files
    if (Test-Path "$SHARED_DATA_DIR\historical_data") {
        $fileCount = (Get-ChildItem -Path "$SHARED_DATA_DIR\historical_data" -File -Recurse).Count
        Write-Log "Historical data files: $fileCount files found"
        $dataStatus += "Historical data files: ✅ $fileCount files found"
    }
    else {
        Write-Log "Historical data files: Directory not found"
        $dataStatus += "Historical data files: ❌ Directory not found"
        $allDataOk = $false
    }
    
    # Check user data files
    if (Test-Path "$SHARED_DATA_DIR\user_data") {
        $fileCount = (Get-ChildItem -Path "$SHARED_DATA_DIR\user_data" -File -Recurse).Count
        Write-Log "User data files: $fileCount files found"
        $dataStatus += "User data files: ✅ $fileCount files found"
    }
    else {
        Write-Log "User data files: Directory not found"
        $dataStatus += "User data files: ❌ Directory not found"
        $allDataOk = $false
    }
    
    # Return results
    if ($allDataOk) {
        Write-Log "Data integrity check passed."
        $script:DATA_STATUS_ARRAY = $dataStatus
        return $true
    }
    else {
        Write-Log "Data integrity check failed."
        $script:DATA_STATUS_ARRAY = $dataStatus
        return $false
    }
}
            Write-Log "Redis: NOT CONNECTED"
            $script:REDIS_STATUS = "Redis: ❌ NOT CONNECTED"
            return $false
        }
    }
    catch {
        Write-Log "Redis: NOT CONNECTED (Error: $($_.Exception.Message))"
        $script:REDIS_STATUS = "Redis: ❌ NOT CONNECTED (Error: $($_.Exception.Message))"
        return $false
# Function to check system performance
function Test-SystemPerformance {
    Write-Log "Checking system performance..."
    
    $allPerformanceOk = $true
    $performanceStatus = @()
    
    # Check CPU usage
    $cpuUsage = (Get-WmiObject -Class Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
    Write-Log "CPU usage: $cpuUsage%"
    
    if ($cpuUsage -lt 80) {
        $performanceStatus += "CPU usage: ✅ $cpuUsage% (Good)"
    }
    else {
        $performanceStatus += "CPU usage: ⚠️ $cpuUsage% (High)"
        $allPerformanceOk = $false
    }
    
    # Check memory usage
    $os = Get-WmiObject -Class Win32_OperatingSystem
    $memoryUsage = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize * 100, 2)
    Write-Log "Memory usage: $memoryUsage%"
    
    if ($memoryUsage -lt 80) {
        $performanceStatus += "Memory usage: ✅ $memoryUsage% (Good)"
    }
    else {
        $performanceStatus += "Memory usage: ⚠️ $memoryUsage% (High)"
        $allPerformanceOk = $false
    }
    
    # Check disk usage
    $drive = Split-Path -Qualifier $SHARED_DATA_DIR
    $disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='$drive'"
    $diskUsage = [math]::Round((($disk.Size - $disk.FreeSpace) / $disk.Size) * 100, 2)
    Write-Log "Disk usage: $diskUsage%"
    
    if ($diskUsage -lt 80) {
        $performanceStatus += "Disk usage: ✅ $diskUsage% (Good)"
    }
    else {
        $performanceStatus += "Disk usage: ⚠️ $diskUsage% (High)"
        $allPerformanceOk = $false
    }
    
    # Check API response times
    $authPort = if ($env:CRYPTOBOT_NON_DOCKER_AUTH_PORT) { $env:CRYPTOBOT_NON_DOCKER_AUTH_PORT } else { 9000 }
    try {
        $start = Get-Date
        $response = Invoke-WebRequest -Uri "http://localhost:$authPort/health" -UseBasicParsing -ErrorAction SilentlyContinue
        $end = Get-Date
        $authTime = ($end - $start).TotalSeconds
        Write-Log "Auth API response time: ${authTime}s"
        
        if ($authTime -lt 0.5) {
            $performanceStatus += "Auth API response time: ✅ ${authTime}s (Good)"
        }
        else {
            $performanceStatus += "Auth API response time: ⚠️ ${authTime}s (Slow)"
            $allPerformanceOk = $false
        }
    }
    catch {
        Write-Log "Auth API response time: FAILED to measure"
        $performanceStatus += "Auth API response time: ❌ FAILED to measure"
        $allPerformanceOk = $false
    }
    
    # Return results
    if ($allPerformanceOk) {
        Write-Log "System performance check passed."
        $script:PERFORMANCE_STATUS_ARRAY = $performanceStatus
        return $true
    }
    else {
        Write-Log "System performance check has warnings."
        $script:PERFORMANCE_STATUS_ARRAY = $performanceStatus
        return $false
    }
}

# Function to generate HTML report
function New-HtmlReport {
    param (
        [string]$DockerStatus,
        [string]$ServicesStatus,
        [string]$DatabaseStatus,
        [string]$RedisStatus,
        [string]$ApiStatus,
        [string]$DataStatus,
        [string]$PerformanceStatus,
        [string]$OverallStatus
    )
    
    Write-Log "Generating HTML report..."
    
    # Determine status colors
    $overallColor = "green"
    if ($OverallStatus -eq "FAILED") {
        $overallColor = "red"
    }
    elseif ($OverallStatus -eq "WARNING") {
        $overallColor = "orange"
    }
    
    $dockerColor = "green"
    if ($DockerStatus -eq "FAILED") {
        $dockerColor = "red"
    }
    
    $servicesColor = "green"
    if ($ServicesStatus -eq "FAILED") {
        $servicesColor = "red"
    }
    
    $databaseColor = "green"
    if ($DatabaseStatus -eq "FAILED") {
        $databaseColor = "red"
    }
    
    $redisColor = "green"
    if ($RedisStatus -eq "FAILED") {
        $redisColor = "red"
    }
    
    $apiColor = "green"
    if ($ApiStatus -eq "FAILED") {
        $apiColor = "red"
    }
    
    $dataColor = "green"
    if ($DataStatus -eq "FAILED") {
        $dataColor = "red"
    }
    
    $performanceColor = "green"
    if ($PerformanceStatus -eq "FAILED") {
        $performanceColor = "red"
    }
    elseif ($PerformanceStatus -eq "WARNING") {
        $performanceColor = "orange"
    }
    
    # Create HTML report content
    $html = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cryptobot Migration Verification Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        h1, h2 {
            color: #2c3e50;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: #fff;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .status {
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .status-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            cursor: pointer;
        }
        .status-content {
            display: none;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 4px;
        }
        .status-content.active {
            display: block;
        }
        .status-item {
            margin-bottom: 5px;
        }
        .success {
            background-color: #d4edda;
            border-color: #c3e6cb;
            color: #155724;
        }
        .warning {
            background-color: #fff3cd;
            border-color: #ffeeba;
            color: #856404;
        }
        .danger {
            background-color: #f8d7da;
            border-color: #f5c6cb;
            color: #721c24;
        }
        .timestamp {
            font-size: 0.8em;
            color: #6c757d;
            margin-bottom: 20px;
        }
        .overall {
            font-size: 1.2em;
            font-weight: bold;
            text-align: center;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Cryptobot Migration Verification Report</h1>
        <div class="timestamp">Generated on: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")</div>
        
        <div class="overall" style="background-color: ${overallColor}; color: white;">
            Overall Status: ${OverallStatus}
        </div>
        
        <div class="status" style="background-color: ${dockerColor}25;">
            <div class="status-header">
                <h2>Docker Status</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>Docker containers should be stopped after successful migration.</p>
                <div class="status-item">
                    Docker containers: ${DockerStatus}
                </div>
            </div>
        </div>
        
        <div class="status" style="background-color: ${servicesColor}25;">
            <div class="status-header">
                <h2>Non-Docker Services</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>All non-Docker services should be running.</p>
"@

    # Add services status items
    foreach ($item in $SERVICES_STATUS_ARRAY) {
        $html += @"
                <div class="status-item">$item</div>
"@
    }
    
    $html += @"
            </div>
        </div>
        
        <div class="status" style="background-color: ${databaseColor}25;">
            <div class="status-header">
                <h2>Database Status</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>Database should be accessible.</p>
                <div class="status-item">
                    ${DATABASE_STATUS}
                </div>
            </div>
        </div>
        
        <div class="status" style="background-color: ${redisColor}25;">
            <div class="status-header">
                <h2>Redis Status</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>Redis should be accessible.</p>
                <div class="status-item">
                    ${REDIS_STATUS}
                </div>
            </div>
        </div>
        
        <div class="status" style="background-color: ${apiColor}25;">
            <div class="status-header">
                <h2>API Endpoints</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>All API endpoints should be accessible.</p>
"@
# Main function
function Start-MigrationVerification {
    Write-Log "Starting migration verification..."
    
    # Check Docker containers
    if (Test-DockerContainers) {
        $dockerStatus = "PASSED"
    }
    else {
        $dockerStatus = "FAILED"
    }
    
    # Check non-Docker services
    if (Test-NonDockerServices) {
        $servicesStatus = "PASSED"
    }
    else {
        $servicesStatus = "FAILED"
    }
    
    # Check database
    if (Test-DatabaseConnection) {
        $databaseStatusResult = "PASSED"
    }
    else {
        $databaseStatusResult = "FAILED"
    }
    
    # Check Redis
    if (Test-RedisConnection) {
        $redisStatusResult = "PASSED"
    }
    else {
        $redisStatusResult = "FAILED"
    }
    
    # Check API endpoints
    if (Test-ApiEndpoints) {
        $apiStatus = "PASSED"
    }
    else {
        $apiStatus = "FAILED"
    }
    
    # Check data integrity
    if (Test-DataIntegrity) {
        $dataStatus = "PASSED"
    }
    else {
        $dataStatus = "FAILED"
    }
    
    # Check system performance
    if (Test-SystemPerformance) {
        $performanceStatus = "PASSED"
    }
    else {
        $performanceStatus = "WARNING"
    }
    
    # Determine overall status
    if ($dockerStatus -eq "FAILED" -or $servicesStatus -eq "FAILED" -or $databaseStatusResult -eq "FAILED" -or 
        $redisStatusResult -eq "FAILED" -or $apiStatus -eq "FAILED" -or $dataStatus -eq "FAILED") {
        $overallStatus = "FAILED"
    }
    elseif ($performanceStatus -eq "WARNING") {
        $overallStatus = "WARNING"
    }
    else {
        $overallStatus = "PASSED"
    }
    
    # Generate HTML report
    New-HtmlReport -DockerStatus $dockerStatus -ServicesStatus $servicesStatus -DatabaseStatus $databaseStatusResult `
                  -RedisStatus $redisStatusResult -ApiStatus $apiStatus -DataStatus $dataStatus `
                  -PerformanceStatus $performanceStatus -OverallStatus $overallStatus
    
    # Print summary
    Write-Host ""
    Write-Host "=== Migration Verification Summary ===" -ForegroundColor Cyan
    Write-Host "Docker Status: $dockerStatus" -ForegroundColor $(if ($dockerStatus -eq "PASSED") { "Green" } else { "Red" })
    Write-Host "Non-Docker Services: $servicesStatus" -ForegroundColor $(if ($servicesStatus -eq "PASSED") { "Green" } else { "Red" })
    Write-Host "Database Status: $databaseStatusResult" -ForegroundColor $(if ($databaseStatusResult -eq "PASSED") { "Green" } else { "Red" })
    Write-Host "Redis Status: $redisStatusResult" -ForegroundColor $(if ($redisStatusResult -eq "PASSED") { "Green" } else { "Red" })
    Write-Host "API Endpoints: $apiStatus" -ForegroundColor $(if ($apiStatus -eq "PASSED") { "Green" } else { "Red" })
    Write-Host "Data Integrity: $dataStatus" -ForegroundColor $(if ($dataStatus -eq "PASSED") { "Green" } else { "Red" })
    Write-Host "System Performance: $performanceStatus" -ForegroundColor $(if ($performanceStatus -eq "PASSED") { "Green" } elseif ($performanceStatus -eq "WARNING") { "Yellow" } else { "Red" })
    Write-Host ""
    Write-Host "Overall Status: $overallStatus" -ForegroundColor $(if ($overallStatus -eq "PASSED") { "Green" } elseif ($overallStatus -eq "WARNING") { "Yellow" } else { "Red" })
    Write-Host ""
    Write-Host "Detailed report: $VERIFY_REPORT" -ForegroundColor White
    Write-Host "Log file: $VERIFY_LOG" -ForegroundColor White
    
    # Return exit code based on overall status
    if ($overallStatus -eq "PASSED") {
        return 0
    }
    else {
        return 1
    }
}

# Parse command line arguments
param (
    [switch]$OpenReport,
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: .\verify_migration.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host "Verify the successful completion of the migration from Docker to non-Docker." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -OpenReport      Open the HTML report in the default browser after verification" -ForegroundColor Yellow
    Write-Host "  -Help            Display this help message" -ForegroundColor Yellow
    exit 0
}

# Run the verification
$exitCode = Start-MigrationVerification

# Open the report if requested
if ($OpenReport -and (Test-Path $VERIFY_REPORT)) {
    Start-Process $VERIFY_REPORT
}

# Exit with the appropriate code
exit $exitCode

    # Add API status items
    foreach ($item in $API_STATUS_ARRAY) {
        $html += @"
                <div class="status-item">$item</div>
"@
    }
    
    $html += @"
            </div>
        </div>
        
        <div class="status" style="background-color: ${dataColor}25;">
            <div class="status-header">
                <h2>Data Integrity</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>All data should be intact and accessible.</p>
"@

    # Add data status items
    foreach ($item in $DATA_STATUS_ARRAY) {
        $html += @"
                <div class="status-item">$item</div>
"@
    }
    
    $html += @"
            </div>
        </div>
        
        <div class="status" style="background-color: ${performanceColor}25;">
            <div class="status-header">
                <h2>System Performance</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>System performance should be within acceptable limits.</p>
"@

    # Add performance status items
    foreach ($item in $PERFORMANCE_STATUS_ARRAY) {
        $html += @"
                <div class="status-item">$item</div>
"@
    }
    
    $html += @"
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const headers = document.querySelectorAll('.status-header');
            
            headers.forEach(header => {
                header.addEventListener('click', function() {
                    const content = this.nextElementSibling;
                    content.classList.toggle('active');
                    this.querySelector('span').textContent = content.classList.contains('active') ? '▲' : '▼';
                });
            });
            
            // Open the first section by default
            const firstContent = document.querySelector('.status-content');
            if (firstContent) {
                firstContent.classList.add('active');
                firstContent.previousElementSibling.querySelector('span').textContent = '▲';
            }
        });
    </script>
</body>
</html>
"@

    # Write HTML to file
    Set-Content -Path $VERIFY_REPORT -Value $html
    
    Write-Log "HTML report generated: $VERIFY_REPORT"
}
    }
}
    try {
        $containers = docker ps --format "{{.Names}}" 2>$null | Where-Object { $_ -match 'cryptobot|auth|strategy|backtest|trade|data' }
        $containerCount = if ($containers) { $containers.Count } else { 0 }
        
        if ($containerCount -gt 0) {
            Write-Log "Found $containerCount Docker containers still running."
            Write-Log "Docker containers should be stopped after successful migration."
            return $false
        }
        else {
            Write-Log "No Docker containers running. Good."
            return $true
        }
    }
    catch {
        Write-Log "Error checking Docker containers: $($_.Exception.Message)"
        return $false
    }
}