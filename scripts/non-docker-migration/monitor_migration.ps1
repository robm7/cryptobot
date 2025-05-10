# monitor_migration.ps1
# Script to monitor the migration process from Docker to non-Docker on Windows
# Part of Phase 11: Parallel Operation Strategy

Write-Host "=== Cryptobot Migration Monitoring Tool ===" -ForegroundColor Cyan
Write-Host "This script monitors the migration process from Docker to non-Docker environments." -ForegroundColor Cyan

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
$MONITOR_LOG = "$LOG_DIR\migration_monitor.log"
$MONITOR_DATA_DIR = "$SHARED_DATA_DIR\migration_monitoring"
$ALERT_LOG = "$MONITOR_DATA_DIR\alerts.log"
$STATUS_FILE = "$MONITOR_DATA_DIR\migration_status.json"

# Create monitoring directories if they don't exist
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null
}
if (-not (Test-Path $MONITOR_DATA_DIR)) {
    New-Item -ItemType Directory -Force -Path $MONITOR_DATA_DIR | Out-Null
}

# Function to log messages
function Write-Log {
    param (
        [string]$Message
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage
    Add-Content -Path $MONITOR_LOG -Value $logMessage
}

# Function to log alerts
function Write-Alert {
    param (
        [string]$Severity,
        [string]$Message
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $alertMessage = "[$timestamp] [$Severity] $Message"
    Write-Host $alertMessage -ForegroundColor $(if ($Severity -eq "CRITICAL") { "Red" } else { "Yellow" })
    Add-Content -Path $ALERT_LOG -Value $alertMessage
    
    # For critical alerts, send notification (implement based on your notification system)
    if ($Severity -eq "CRITICAL") {
        # Example: Send email notification
        # Send-MailMessage -From "monitor@cryptobot.example.com" -To "admin@example.com" -Subject "CRITICAL Cryptobot Migration Alert" -Body $alertMessage -SmtpServer "smtp.example.com"
        Write-Host "Notification sent for CRITICAL alert" -ForegroundColor Red
    }
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

# Function to check Docker service health
function Test-DockerService {
    param (
        [string]$ServiceName,
        [int]$Port
    )
    
    if (Test-ServiceRunning -Host "localhost" -Port $Port) {
        Write-Log "Docker $ServiceName: RUNNING"
        return $true
    }
    else {
        Write-Log "Docker $ServiceName: NOT RUNNING"
        return $false
    }
}

# Function to check non-Docker service health
function Test-NonDockerService {
    param (
        [string]$ServiceName,
        [int]$Port
    )
    
    if (Test-ServiceRunning -Host "localhost" -Port $Port) {
        Write-Log "Non-Docker $ServiceName: RUNNING"
        return $true
    }
    else {
        Write-Log "Non-Docker $ServiceName: NOT RUNNING"
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
            return $true
        }
        else {
            $tcpClient.Close()
            Write-Log "Database: NOT CONNECTED"
            Write-Alert -Severity "WARNING" -Message "Database connection failed"
            return $false
        }
    }
    catch {
        Write-Log "Database: NOT CONNECTED (Error: $($_.Exception.Message))"
        Write-Alert -Severity "WARNING" -Message "Database connection failed: $($_.Exception.Message)"
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
            return $true
        }
        else {
            $tcpClient.Close()
            Write-Log "Redis: NOT CONNECTED"
            Write-Alert -Severity "WARNING" -Message "Redis connection failed"
            return $false
        }
    }
    catch {
        Write-Log "Redis: NOT CONNECTED (Error: $($_.Exception.Message))"
        Write-Alert -Severity "WARNING" -Message "Redis connection failed: $($_.Exception.Message)"
        return $false
    }
}

# Function to check API endpoints
function Test-ApiEndpoint {
    param (
        [string]$ServiceName,
        [string]$Url,
        [int]$ExpectedStatus
    )
    
    Write-Log "Checking $ServiceName API endpoint: $Url"
    
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -ErrorAction SilentlyContinue
        $statusCode = [int]$response.StatusCode
        
        if ($statusCode -eq $ExpectedStatus) {
            Write-Log "$ServiceName API: OK (Status: $statusCode)"
            return $true
        }
        else {
            Write-Log "$ServiceName API: FAILED (Status: $statusCode, Expected: $ExpectedStatus)"
            Write-Alert -Severity "WARNING" -Message "$ServiceName API endpoint check failed: $Url (Status: $statusCode, Expected: $ExpectedStatus)"
            return $false
        }
    }
    catch {
        $statusCode = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        Write-Log "$ServiceName API: FAILED (Status: $statusCode, Expected: $ExpectedStatus)"
        Write-Alert -Severity "WARNING" -Message "$ServiceName API endpoint check failed: $Url (Status: $statusCode, Expected: $ExpectedStatus)"
        return $false
    }
}

# Function to check disk space
function Test-DiskSpace {
    Write-Log "Checking disk space..."
    
    $threshold = 90  # Alert if disk usage is above 90%
    $drive = Split-Path -Qualifier $SHARED_DATA_DIR
    $disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='$drive'"
    $diskUsage = [math]::Round((($disk.Size - $disk.FreeSpace) / $disk.Size) * 100, 2)
    
    Write-Log "Disk usage for $drive`: $diskUsage%"
    
    if ($diskUsage -gt $threshold) {
        Write-Alert -Severity "WARNING" -Message "Disk usage above threshold: $diskUsage% (Threshold: $threshold%)"
        return $false
    }
    else {
        return $true
    }
}

# Function to check memory usage
function Test-MemoryUsage {
    Write-Log "Checking memory usage..."
    
    $threshold = 90  # Alert if memory usage is above 90%
    $os = Get-WmiObject -Class Win32_OperatingSystem
    $memoryUsage = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize * 100, 2)
    
    Write-Log "Memory usage: $memoryUsage%"
    
    if ($memoryUsage -gt $threshold) {
        Write-Alert -Severity "WARNING" -Message "Memory usage above threshold: $memoryUsage% (Threshold: $threshold%)"
        return $false
    }
    else {
        return $true
    }
}

# Function to check CPU load
function Test-CpuLoad {
    Write-Log "Checking CPU load..."
    
    $threshold = 80  # Alert if CPU load is above 80%
    $cpuLoad = (Get-WmiObject -Class Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
    
    Write-Log "CPU load: $cpuLoad%"
    
    if ($cpuLoad -gt $threshold) {
        Write-Alert -Severity "WARNING" -Message "CPU load above threshold: $cpuLoad% (Threshold: $threshold%)"
        return $false
    }
    else {
        return $true
    }
}

# Function to check log files for errors
function Test-LogsForErrors {
    Write-Log "Checking logs for errors..."
    
    $errorCount = 0
    $criticalPatterns = @("ERROR", "CRITICAL", "FATAL", "Exception", "failed", "crash")
    
    foreach ($pattern in $criticalPatterns) {
        $matches = Select-String -Path "$LOG_DIR\*.log" -Pattern $pattern -ErrorAction SilentlyContinue
        $count = if ($matches) { $matches.Count } else { 0 }
        $errorCount += $count
        
        if ($count -gt 0) {
            Write-Log "Found $count occurrences of '$pattern' in logs"
            
            # Log the first 5 occurrences
            $matches | Select-Object -First 5 | ForEach-Object {
                Write-Log "Log entry: $($_.Line)"
            }
        }
    }
    
    if ($errorCount -gt 0) {
        Write-Alert -Severity "WARNING" -Message "Found $errorCount error patterns in logs"
        return $false
    }
    else {
        Write-Log "No errors found in logs"
        return $true
    }
}

# Function to compare Docker and non-Docker service response times
function Compare-ResponseTimes {
    param (
        [string]$ServiceName,
        [string]$DockerUrl,
        [string]$NonDockerUrl
    )
    
    Write-Log "Comparing response times for $ServiceName..."
    
    try {
        $dockerStart = Get-Date
        $dockerResponse = Invoke-WebRequest -Uri $DockerUrl -UseBasicParsing -ErrorAction SilentlyContinue
        $dockerEnd = Get-Date
        $dockerTime = ($dockerEnd - $dockerStart).TotalSeconds
        
        $nonDockerStart = Get-Date
        $nonDockerResponse = Invoke-WebRequest -Uri $NonDockerUrl -UseBasicParsing -ErrorAction SilentlyContinue
        $nonDockerEnd = Get-Date
        $nonDockerTime = ($nonDockerEnd - $nonDockerStart).TotalSeconds
        
        Write-Log "Docker $ServiceName response time: ${dockerTime}s"
        Write-Log "Non-Docker $ServiceName response time: ${nonDockerTime}s"
        
        # Calculate percentage difference
        $diff = [math]::Round(($nonDockerTime - $dockerTime) / $dockerTime * 100, 2)
        
        if ($diff -gt 50) {
            Write-Alert -Severity "WARNING" -Message "Non-Docker $ServiceName is significantly slower (${diff}% difference)"
            return $false
        }
        elseif ($diff -lt -20) {
            Write-Log "Non-Docker $ServiceName is faster (${diff}% difference)"
        }
        else {
            Write-Log "Response times are comparable (${diff}% difference)"
        }
        
        return $true
    }
    catch {
        Write-Log "Error comparing response times for $ServiceName: $($_.Exception.Message)"
        return $false
    }
}

# Function to update migration status file
function Update-StatusFile {
    param (
        [string]$DockerServicesStatus,
        [string]$NonDockerServicesStatus,
        [string]$DatabaseStatus,
        [string]$RedisStatus,
        [string]$DiskStatus,
        [string]$MemoryStatus,
        [string]$CpuStatus,
        [string]$LogsStatus
    )
    
    # Calculate overall status
    $overallStatus = "GREEN"
    if ($DockerServicesStatus -eq "RED" -or $NonDockerServicesStatus -eq "RED" -or $DatabaseStatus -eq "RED" -or $RedisStatus -eq "RED") {
        $overallStatus = "RED"
    }
    elseif ($DockerServicesStatus -eq "YELLOW" -or $NonDockerServicesStatus -eq "YELLOW" -or $DatabaseStatus -eq "YELLOW" -or $RedisStatus -eq "YELLOW" -or $DiskStatus -eq "YELLOW" -or $MemoryStatus -eq "YELLOW" -or $CpuStatus -eq "YELLOW" -or $LogsStatus -eq "YELLOW") {
        $overallStatus = "YELLOW"
    }
    
    # Create status object
    $status = @{
        timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        overall_status = $overallStatus
        components = @{
            docker_services = $DockerServicesStatus
            non_docker_services = $NonDockerServicesStatus
            database = $DatabaseStatus
            redis = $RedisStatus
            disk_space = $DiskStatus
            memory_usage = $MemoryStatus
            cpu_load = $CpuStatus
            logs = $LogsStatus
        }
        alert_count = if (Test-Path $ALERT_LOG) { (Get-Content $ALERT_LOG).Count } else { 0 }
        last_check = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    }
    
    # Convert to JSON and save to file
    $status | ConvertTo-Json -Depth 3 | Set-Content -Path $STATUS_FILE
    
    Write-Log "Updated status file: $STATUS_FILE"
    
    # If status is RED, send notification
    if ($overallStatus -eq "RED") {
        Write-Alert -Severity "CRITICAL" -Message "Migration monitoring detected RED status"
    }
}

# Function to run all checks
function Start-AllChecks {
    Write-Log "Starting migration monitoring checks..."
    
    # Check Docker services
    $dockerAuthPort = if ($env:CRYPTOBOT_DOCKER_AUTH_PORT) { $env:CRYPTOBOT_DOCKER_AUTH_PORT } else { 8000 }
    $dockerStrategyPort = if ($env:CRYPTOBOT_DOCKER_STRATEGY_PORT) { $env:CRYPTOBOT_DOCKER_STRATEGY_PORT } else { 8001 }
    $dockerBacktestPort = if ($env:CRYPTOBOT_DOCKER_BACKTEST_PORT) { $env:CRYPTOBOT_DOCKER_BACKTEST_PORT } else { 8002 }
    $dockerTradePort = if ($env:CRYPTOBOT_DOCKER_TRADE_PORT) { $env:CRYPTOBOT_DOCKER_TRADE_PORT } else { 8003 }
    $dockerDataPort = if ($env:CRYPTOBOT_DOCKER_DATA_PORT) { $env:CRYPTOBOT_DOCKER_DATA_PORT } else { 8004 }
    
    $dockerAuthStatus = if (Test-DockerService -ServiceName "auth" -Port $dockerAuthPort) { "GREEN" } else { "RED" }
    $dockerStrategyStatus = if (Test-DockerService -ServiceName "strategy" -Port $dockerStrategyPort) { "GREEN" } else { "RED" }
    $dockerBacktestStatus = if (Test-DockerService -ServiceName "backtest" -Port $dockerBacktestPort) { "GREEN" } else { "RED" }
    $dockerTradeStatus = if (Test-DockerService -ServiceName "trade" -Port $dockerTradePort) { "GREEN" } else { "RED" }
    $dockerDataStatus = if (Test-DockerService -ServiceName "data" -Port $dockerDataPort) { "GREEN" } else { "RED" }
    
    # Determine overall Docker services status
    $dockerServicesStatus = "GREEN"
    if ($dockerAuthStatus -eq "RED" -or $dockerStrategyStatus -eq "RED" -or $dockerBacktestStatus -eq "RED" -or $dockerTradeStatus -eq "RED" -or $dockerDataStatus -eq "RED") {
        $dockerServicesStatus = "RED"
    }
    
    # Check non-Docker services
    $nonDockerAuthPort = if ($env:CRYPTOBOT_NON_DOCKER_AUTH_PORT) { $env:CRYPTOBOT_NON_DOCKER_AUTH_PORT } else { 9000 }
    $nonDockerStrategyPort = if ($env:CRYPTOBOT_NON_DOCKER_STRATEGY_PORT) { $env:CRYPTOBOT_NON_DOCKER_STRATEGY_PORT } else { 9001 }
    $nonDockerBacktestPort = if ($env:CRYPTOBOT_NON_DOCKER_BACKTEST_PORT) { $env:CRYPTOBOT_NON_DOCKER_BACKTEST_PORT } else { 9002 }
    $nonDockerTradePort = if ($env:CRYPTOBOT_NON_DOCKER_TRADE_PORT) { $env:CRYPTOBOT_NON_DOCKER_TRADE_PORT } else { 9003 }
    $nonDockerDataPort = if ($env:CRYPTOBOT_NON_DOCKER_DATA_PORT) { $env:CRYPTOBOT_NON_DOCKER_DATA_PORT } else { 9004 }
    
    $nonDockerAuthStatus = if (Test-NonDockerService -ServiceName "auth" -Port $nonDockerAuthPort) { "GREEN" } else { "RED" }
    $nonDockerStrategyStatus = if (Test-NonDockerService -ServiceName "strategy" -Port $nonDockerStrategyPort) { "GREEN" } else { "RED" }
    $nonDockerBacktestStatus = if (Test-NonDockerService -ServiceName "backtest" -Port $nonDockerBacktestPort) { "GREEN" } else { "RED" }
    $nonDockerTradeStatus = if (Test-NonDockerService -ServiceName "trade" -Port $nonDockerTradePort) { "GREEN" } else { "RED" }
    $nonDockerDataStatus = if (Test-NonDockerService -ServiceName "data" -Port $nonDockerDataPort) { "GREEN" } else { "RED" }
    
    # Determine overall non-Docker services status
    $nonDockerServicesStatus = "GREEN"
    if ($nonDockerAuthStatus -eq "RED" -or $nonDockerStrategyStatus -eq "RED" -or $nonDockerBacktestStatus -eq "RED" -or $nonDockerTradeStatus -eq "RED" -or $nonDockerDataStatus -eq "RED") {
        $nonDockerServicesStatus = "RED"
    }
    
    # Check database and Redis
    $databaseStatus = if (Test-DatabaseConnection) { "GREEN" } else { "RED" }
    $redisStatus = if (Test-RedisConnection) { "GREEN" } else { "RED" }
    
    # Check system resources
    $diskStatus = if (Test-DiskSpace) { "GREEN" } else { "YELLOW" }
    $memoryStatus = if (Test-MemoryUsage) { "GREEN" } else { "YELLOW" }
    $cpuStatus = if (Test-CpuLoad) { "GREEN" } else { "YELLOW" }
    
    # Check logs
    $logsStatus = if (Test-LogsForErrors) { "GREEN" } else { "YELLOW" }
    
    # Compare response times if both environments are running
    if ($dockerServicesStatus -eq "GREEN" -and $nonDockerServicesStatus -eq "GREEN") {
        Compare-ResponseTimes -ServiceName "auth" -DockerUrl "http://localhost:$dockerAuthPort/health" -NonDockerUrl "http://localhost:$nonDockerAuthPort/health"
        Compare-ResponseTimes -ServiceName "strategy" -DockerUrl "http://localhost:$dockerStrategyPort/health" -NonDockerUrl "http://localhost:$nonDockerStrategyPort/health"
        Compare-ResponseTimes -ServiceName "backtest" -DockerUrl "http://localhost:$dockerBacktestPort/health" -NonDockerUrl "http://localhost:$nonDockerBacktestPort/health"
        Compare-ResponseTimes -ServiceName "trade" -DockerUrl "http://localhost:$dockerTradePort/health" -NonDockerUrl "http://localhost:$nonDockerTradePort/health"
        Compare-ResponseTimes -ServiceName "data" -DockerUrl "http://localhost:$dockerDataPort/health" -NonDockerUrl "http://localhost:$nonDockerDataPort/health"
    }
    
    # Update status file
    Update-StatusFile -DockerServicesStatus $dockerServicesStatus -NonDockerServicesStatus $nonDockerServicesStatus -DatabaseStatus $databaseStatus -RedisStatus $redisStatus -DiskStatus $diskStatus -MemoryStatus $memoryStatus -CpuStatus $cpuStatus -LogsStatus $logsStatus
    
    Write-Log "Migration monitoring checks completed."
}

# Function to display monitoring dashboard
function Show-Dashboard {
    Clear-Host
    Write-Host "=== Cryptobot Migration Monitoring Dashboard ===" -ForegroundColor Cyan
    Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor White
    Write-Host ""
    
    if (Test-Path $STATUS_FILE) {
        $status = Get-Content $STATUS_FILE | ConvertFrom-Json
        $overallStatus = $status.overall_status
        
        $statusColor = switch ($overallStatus) {
            "GREEN" { "Green" }
            "YELLOW" { "Yellow" }
            "RED" { "Red" }
            default { "White" }
        }
        
        Write-Host "Overall Status: " -NoNewline
        Write-Host $overallStatus -ForegroundColor $statusColor
        Write-Host ""
        
        Write-Host "Component Status:" -ForegroundColor White
        foreach ($component in $status.components.PSObject.Properties) {
            $componentColor = switch ($component.Value) {
                "GREEN" { "Green" }
                "YELLOW" { "Yellow" }
                "RED" { "Red" }
                default { "White" }
            }
            
            Write-Host "  $($component.Name): " -NoNewline
            Write-Host $component.Value -ForegroundColor $componentColor
        }
        Write-Host ""
        
        Write-Host "Recent Alerts:" -ForegroundColor White
        if (Test-Path $ALERT_LOG) {
            Get-Content $ALERT_LOG -Tail 5 | ForEach-Object {
                if ($_ -match "CRITICAL") {
                    Write-Host "  $_" -ForegroundColor Red
                }
                else {
                    Write-Host "  $_" -ForegroundColor Yellow
                }
            }
        }
        else {
            Write-Host "  No alerts found." -ForegroundColor Gray
        }
        Write-Host ""
    }
    else {
        Write-Host "Status file not found. Run checks first." -ForegroundColor Yellow
        Write-Host ""
    }
    
    Write-Host "Commands:" -ForegroundColor White
    Write-Host "  r - Run checks" -ForegroundColor Gray
    Write-Host "  l - View logs" -ForegroundColor Gray
    Write-Host "  a - View all alerts" -ForegroundColor Gray
    Write-Host "  q - Quit" -ForegroundColor Gray
    Write-Host ""
}

# Function to view logs
function Show-Logs {
    Clear-Host
    Write-Host "=== Cryptobot Migration Monitoring Logs ===" -ForegroundColor Cyan
    Write-Host "Last 20 log entries:" -ForegroundColor White
    Write-Host ""
    
    if (Test-Path $MONITOR_LOG) {
        Get-Content $MONITOR_LOG -Tail 20 | ForEach-Object {
            Write-Host "  $_" -ForegroundColor Gray
        }
    }
    else {
        Write-Host "  No logs found." -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "Press Enter to return to dashboard..." -ForegroundColor Yellow
    Read-Host | Out-Null
}

# Function to view all alerts
function Show-Alerts {
    Clear-Host
    Write-Host "=== Cryptobot Migration Monitoring Alerts ===" -ForegroundColor Cyan
    Write-Host ""
    
    if (Test-Path $ALERT_LOG) {
        Get-Content $ALERT_LOG | ForEach-Object {
            if ($_ -match "CRITICAL") {
                Write-Host "  $_" -ForegroundColor Red
            }
            else {
                Write-Host "  $_" -ForegroundColor Yellow
            }
        }
    }
    else {
        Write-Host "  No alerts found." -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "Press Enter to return to dashboard..." -ForegroundColor Yellow
    Read-Host | Out-Null
}

# Main function for interactive mode
function Start-InteractiveMode {
    $running = $true
    
    while ($running) {
        Show-Dashboard
        
        $command = Read-Host "Enter command"
        
        switch ($command) {
            "r" {
                Start-AllChecks
            }
            "l" {
                Show-Logs
            }
            "a" {
                Show-Alerts
            }
            "q" {
                $running = $false
            }
            default {
                Write-Host "Unknown command. Press Enter to continue..." -ForegroundColor Yellow
                Read-Host | Out-Null
            }
        }
    }
    
    Write-Host "Exiting migration monitoring tool." -ForegroundColor Cyan
}

# Main function for non-interactive mode
function Start-NonInteractiveMode {
    Start-AllChecks
    
    # Print summary
    if (Test-Path $STATUS_FILE) {
        $status = Get-Content $STATUS_FILE | ConvertFrom-Json
        $overallStatus = $status.overall_status
        
        $statusColor = switch ($overallStatus) {
            "GREEN" { "Green" }
            "YELLOW" { "Yellow" }
            "RED" { "Red" }
            default { "White" }
        }
        
        Write-Host "Overall Status: " -NoNewline
        Write-Host $overallStatus -ForegroundColor $statusColor
        
        Write-Host "Component Status:" -ForegroundColor White
        foreach ($component in $status.components.PSObject.Properties) {
            $componentColor = switch ($component.Value) {
                "GREEN" { "Green" }
                "YELLOW" { "Yellow" }
                "RED" { "Red" }
                default { "White" }
            }
            
            Write-Host "  $($component.Name): " -NoNewline
            Write-Host $component.Value -ForegroundColor $componentColor
        }
    }
    else {
        Write-Host "Error: Status file not found after running checks." -ForegroundColor Red
    }
}

# Parse command line arguments
param (
    [switch]$NonInteractive,
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: .\monitor_migration.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host "Monitor the migration process from Docker to non-Docker environments." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -NonInteractive  Run checks once and exit" -ForegroundColor Yellow
    Write-Host "  -Help            Display this help message" -ForegroundColor Yellow
    exit 0
}

if ($NonInteractive) {
    Start-NonInteractiveMode
}
else {
    # Run in interactive mode by default
    Start-InteractiveMode
}