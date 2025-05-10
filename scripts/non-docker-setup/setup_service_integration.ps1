# Cryptobot Service Integration Setup Script for Windows

# Function to display messages
function Log {
    param (
        [string]$Message
    )
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
}

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Log "Error: This script must be run as Administrator. Please restart PowerShell as Administrator and try again."
    exit 1
}

# Configuration directories
$AuthConfigDir = "C:\ProgramData\Cryptobot\auth"
$StrategyConfigDir = "C:\ProgramData\Cryptobot\strategy"
$BacktestConfigDir = "C:\ProgramData\Cryptobot\backtest"
$TradeConfigDir = "C:\ProgramData\Cryptobot\trade"
$DataConfigDir = "C:\ProgramData\Cryptobot\data"
$McpConfigDir = "C:\ProgramData\Cryptobot\mcp"

# Check if all configuration files exist
if (-not (Test-Path "$AuthConfigDir\config.json") -or
    -not (Test-Path "$StrategyConfigDir\config.json") -or
    -not (Test-Path "$BacktestConfigDir\config.json") -or
    -not (Test-Path "$TradeConfigDir\config.json") -or
    -not (Test-Path "$DataConfigDir\config.json") -or
    -not (Test-Path "$McpConfigDir\config.json")) {
    Log "Error: One or more service configuration files are missing."
    Log "Please run the service installation scripts first."
    exit 1
}

Log "Setting up service integration and communication..."

# Function to generate API keys for inter-service communication
function Generate-ApiKey {
    # Generate a random 32-character API key
    $bytes = New-Object Byte[] 16
    $rand = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rand.GetBytes($bytes)
    return [System.BitConverter]::ToString($bytes) -replace '-', ''
}

# Update configuration files with API keys for inter-service communication
Log "Generating and configuring API keys for inter-service communication..."

# Generate API keys
$AuthApiKey = Generate-ApiKey
$StrategyApiKey = Generate-ApiKey
$BacktestApiKey = Generate-ApiKey
$TradeApiKey = Generate-ApiKey
$DataApiKey = Generate-ApiKey

# Function to update JSON configuration files
function Update-JsonConfig {
    param (
        [string]$FilePath,
        [scriptblock]$UpdateScript
    )
    
    $config = Get-Content -Path $FilePath -Raw | ConvertFrom-Json
    $config = & $UpdateScript $config
    $config | ConvertTo-Json -Depth 10 | Set-Content -Path $FilePath
}

# Update Auth Service config
Log "Updating Auth Service configuration..."
Update-JsonConfig -FilePath "$AuthConfigDir\config.json" -UpdateScript {
    param($config)
    
    if (-not $config.PSObject.Properties.Name.Contains("api_keys")) {
        $config | Add-Member -NotePropertyName "api_keys" -NotePropertyValue @{}
    }
    
    $config.api_keys = @{
        "strategy_service" = $StrategyApiKey
        "backtest_service" = $BacktestApiKey
        "trade_service" = $TradeApiKey
        "data_service" = $DataApiKey
    }
    
    return $config
}

# Update Strategy Service config
Log "Updating Strategy Service configuration..."
Update-JsonConfig -FilePath "$StrategyConfigDir\config.json" -UpdateScript {
    param($config)
    
    if (-not $config.PSObject.Properties.Name.Contains("auth_service")) {
        $config | Add-Member -NotePropertyName "auth_service" -NotePropertyValue @{}
    }
    
    $config.auth_service.api_key = $StrategyApiKey
    $config.auth_service.url = "http://localhost:8000"
    
    if (-not $config.PSObject.Properties.Name.Contains("backtest_service")) {
        $config | Add-Member -NotePropertyName "backtest_service" -NotePropertyValue @{}
    }
    
    $config.backtest_service.url = "http://localhost:8002"
    
    if (-not $config.PSObject.Properties.Name.Contains("data_service")) {
        $config | Add-Member -NotePropertyName "data_service" -NotePropertyValue @{}
    }
    
    $config.data_service.url = "http://localhost:8003"
    
    return $config
}

# Update Backtest Service config
Log "Updating Backtest Service configuration..."
Update-JsonConfig -FilePath "$BacktestConfigDir\config.json" -UpdateScript {
    param($config)
    
    if (-not $config.PSObject.Properties.Name.Contains("auth_service")) {
        $config | Add-Member -NotePropertyName "auth_service" -NotePropertyValue @{}
    }
    
    $config.auth_service.api_key = $BacktestApiKey
    $config.auth_service.url = "http://localhost:8000"
    
    if (-not $config.PSObject.Properties.Name.Contains("strategy_service")) {
        $config | Add-Member -NotePropertyName "strategy_service" -NotePropertyValue @{}
    }
    
    $config.strategy_service.url = "http://localhost:8001"
    
    if (-not $config.PSObject.Properties.Name.Contains("data_service")) {
        $config | Add-Member -NotePropertyName "data_service" -NotePropertyValue @{}
    }
    
    $config.data_service.url = "http://localhost:8003"
    
    return $config
}

# Update Trade Service config
Log "Updating Trade Service configuration..."
Update-JsonConfig -FilePath "$TradeConfigDir\config.json" -UpdateScript {
    param($config)
    
    if (-not $config.PSObject.Properties.Name.Contains("auth_service")) {
        $config | Add-Member -NotePropertyName "auth_service" -NotePropertyValue @{}
    }
    
    $config.auth_service.api_key = $TradeApiKey
    $config.auth_service.url = "http://localhost:8000"
    
    if (-not $config.PSObject.Properties.Name.Contains("strategy_service")) {
        $config | Add-Member -NotePropertyName "strategy_service" -NotePropertyValue @{}
    }
    
    $config.strategy_service.url = "http://localhost:8001"
    
    if (-not $config.PSObject.Properties.Name.Contains("data_service")) {
        $config | Add-Member -NotePropertyName "data_service" -NotePropertyValue @{}
    }
    
    $config.data_service.url = "http://localhost:8003"
    
    if (-not $config.PSObject.Properties.Name.Contains("mcp_services")) {
        $config | Add-Member -NotePropertyName "mcp_services" -NotePropertyValue @{}
    }
    
    $config.mcp_services = @{
        "router" = "http://localhost:8010"
        "exchange_gateway" = "http://localhost:8011"
        "paper_trading" = "http://localhost:8012"
    }
    
    return $config
}

# Update Data Service config
Log "Updating Data Service configuration..."
Update-JsonConfig -FilePath "$DataConfigDir\config.json" -UpdateScript {
    param($config)
    
    if (-not $config.PSObject.Properties.Name.Contains("auth_service")) {
        $config | Add-Member -NotePropertyName "auth_service" -NotePropertyValue @{}
    }
    
    $config.auth_service.api_key = $DataApiKey
    $config.auth_service.url = "http://localhost:8000"
    
    return $config
}

# Update MCP Services config
Log "Updating MCP Services configuration..."
Update-JsonConfig -FilePath "$McpConfigDir\config.json" -UpdateScript {
    param($config)
    
    if (-not $config.PSObject.Properties.Name.Contains("auth_service")) {
        $config | Add-Member -NotePropertyName "auth_service" -NotePropertyValue @{}
    }
    
    $config.auth_service = @{
        "url" = "http://localhost:8000"
        "api_key" = $AuthApiKey
    }
    
    if (-not $config.PSObject.Properties.Name.Contains("strategy_service")) {
        $config | Add-Member -NotePropertyName "strategy_service" -NotePropertyValue @{}
    }
    
    $config.strategy_service = @{
        "url" = "http://localhost:8001"
    }
    
    if (-not $config.PSObject.Properties.Name.Contains("backtest_service")) {
        $config | Add-Member -NotePropertyName "backtest_service" -NotePropertyValue @{}
    }
    
    $config.backtest_service = @{
        "url" = "http://localhost:8002"
    }
    
    if (-not $config.PSObject.Properties.Name.Contains("trade_service")) {
        $config | Add-Member -NotePropertyName "trade_service" -NotePropertyValue @{}
    }
    
    $config.trade_service = @{
        "url" = "http://localhost:8004"
    }
    
    if (-not $config.PSObject.Properties.Name.Contains("data_service")) {
        $config | Add-Member -NotePropertyName "data_service" -NotePropertyValue @{}
    }
    
    $config.data_service = @{
        "url" = "http://localhost:8003"
    }
    
    return $config
}

# Create a service discovery file
Log "Creating service discovery configuration..."
$ServiceDiscoveryFile = "C:\ProgramData\Cryptobot\service_discovery.json"
$serviceDiscovery = @{
    "services" = @{
        "auth" = @{
            "host" = "localhost"
            "port" = 8000
            "url" = "http://localhost:8000"
            "api_key" = $AuthApiKey
        }
        "strategy" = @{
            "host" = "localhost"
            "port" = 8001
            "url" = "http://localhost:8001"
            "api_key" = $StrategyApiKey
        }
        "backtest" = @{
            "host" = "localhost"
            "port" = 8002
            "url" = "http://localhost:8002"
            "api_key" = $BacktestApiKey
        }
        "data" = @{
            "host" = "localhost"
            "port" = 8003
            "url" = "http://localhost:8003"
            "api_key" = $DataApiKey
        }
        "trade" = @{
            "host" = "localhost"
            "port" = 8004
            "url" = "http://localhost:8004"
            "api_key" = $TradeApiKey
        }
        "mcp_router" = @{
            "host" = "localhost"
            "port" = 8010
            "url" = "http://localhost:8010"
        }
        "exchange_gateway" = @{
            "host" = "localhost"
            "port" = 8011
            "url" = "http://localhost:8011"
        }
        "paper_trading" = @{
            "host" = "localhost"
            "port" = 8012
            "url" = "http://localhost:8012"
        }
    }
    "communication" = @{
        "protocol" = "http"
        "timeout" = 30
        "retry_attempts" = 3
        "retry_delay" = 2
    }
}

$serviceDiscovery | ConvertTo-Json -Depth 10 | Set-Content -Path $ServiceDiscoveryFile

# Set proper permissions
$acl = Get-Acl $ServiceDiscoveryFile
$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM", "FullControl", "Allow")
$acl.SetAccessRule($accessRule)
$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "Allow")
$acl.SetAccessRule($accessRule)
Set-Acl $ServiceDiscoveryFile $acl

# Create symbolic links to the service discovery file in each service directory
cmd /c mklink /J "C:\Program Files\Cryptobot\services\auth\service_discovery.json" "$ServiceDiscoveryFile"
cmd /c mklink /J "C:\Program Files\Cryptobot\services\strategy\service_discovery.json" "$ServiceDiscoveryFile"
cmd /c mklink /J "C:\Program Files\Cryptobot\services\backtest\service_discovery.json" "$ServiceDiscoveryFile"
cmd /c mklink /J "C:\Program Files\Cryptobot\services\trade\service_discovery.json" "$ServiceDiscoveryFile"
cmd /c mklink /J "C:\Program Files\Cryptobot\services\data\service_discovery.json" "$ServiceDiscoveryFile"
cmd /c mklink /J "C:\Program Files\Cryptobot\services\mcp\service_discovery.json" "$ServiceDiscoveryFile"

# Create a health check script
Log "Creating health check script..."
$ScriptsDir = "C:\Program Files\Cryptobot\scripts"
New-Item -ItemType Directory -Force -Path $ScriptsDir | Out-Null
$HealthCheckScript = "$ScriptsDir\health_check.ps1"

@"
# Cryptobot Services Health Check Script

# Function to display messages
function Log {
    param (
        [string]`$Message
    )
    Write-Host "`$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - `$Message"
}

# Function to check if a service is running
function Check-Service {
    param (
        [string]`$ServiceName,
        [string]`$Url
    )
    
    Log "Checking `$ServiceName service..."
    try {
        `$response = Invoke-WebRequest -Uri "`$Url/health" -UseBasicParsing -ErrorAction Stop
        if (`$response.StatusCode -eq 200) {
            Log "`$ServiceName service is running."
            return `$true
        } else {
            Log "`$ServiceName service is not responding properly. Status code: `$(`$response.StatusCode)"
            return `$false
        }
    } catch {
        Log "`$ServiceName service is not responding. Error: `$(`$_.Exception.Message)"
        return `$false
    }
}

# Check all services
Log "Starting health check for all Cryptobot services..."

# Load service discovery configuration
`$ServiceDiscoveryFile = "C:\ProgramData\Cryptobot\service_discovery.json"
if (-not (Test-Path `$ServiceDiscoveryFile)) {
    Log "Error: Service discovery configuration file not found."
    exit 1
}

# Check core services
Check-Service -ServiceName "Auth" -Url "http://localhost:8000"
Check-Service -ServiceName "Strategy" -Url "http://localhost:8001"
Check-Service -ServiceName "Backtest" -Url "http://localhost:8002"
Check-Service -ServiceName "Data" -Url "http://localhost:8003"
Check-Service -ServiceName "Trade" -Url "http://localhost:8004"

# Check MCP services
Check-Service -ServiceName "MCP Router" -Url "http://localhost:8010"
Check-Service -ServiceName "Exchange Gateway" -Url "http://localhost:8011"
Check-Service -ServiceName "Paper Trading" -Url "http://localhost:8012"

Log "Health check completed."
"@ | Out-File -FilePath $HealthCheckScript -Encoding utf8

# Create a service restart script
Log "Creating service restart script..."
$RestartScript = "$ScriptsDir\restart_services.ps1"

@"
# Cryptobot Services Restart Script

# Function to display messages
function Log {
    param (
        [string]`$Message
    )
    Write-Host "`$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - `$Message"
}

# Function to restart a Windows service
function Restart-CryptobotService {
    param (
        [string]`$ServiceName
    )
    
    Log "Restarting `$ServiceName service..."
    try {
        Restart-Service -Name `$ServiceName -Force -ErrorAction Stop
        Log "`$ServiceName service restarted successfully."
        return `$true
    } catch {
        Log "Failed to restart `$ServiceName service. Error: `$(`$_.Exception.Message)"
        return `$false
    }
}

# Restart all services in the correct order
Log "Restarting all Cryptobot services..."

# Restart core services
Restart-CryptobotService -ServiceName "CryptobotAuth"
Start-Sleep -Seconds 5
Restart-CryptobotService -ServiceName "CryptobotData"
Start-Sleep -Seconds 5
Restart-CryptobotService -ServiceName "CryptobotStrategy"
Start-Sleep -Seconds 5
Restart-CryptobotService -ServiceName "CryptobotBacktest"
Start-Sleep -Seconds 5
Restart-CryptobotService -ServiceName "CryptobotTrade"
Start-Sleep -Seconds 5

# Restart MCP services
Restart-CryptobotService -ServiceName "CryptobotMcpRouter"
Start-Sleep -Seconds 5
Restart-CryptobotService -ServiceName "CryptobotExchangeGateway"
Start-Sleep -Seconds 5
Restart-CryptobotService -ServiceName "CryptobotPaperTrading"

Log "All services have been restarted."
"@ | Out-File -FilePath $RestartScript -Encoding utf8

Log "Service integration setup completed successfully!"
Log "The services are now configured to communicate with each other."
Log "You can use the following scripts to manage the services:"
Log "  - Health check: $HealthCheckScript"
Log "  - Restart services: $RestartScript"

exit 0