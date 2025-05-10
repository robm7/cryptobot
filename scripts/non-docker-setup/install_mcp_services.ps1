# Cryptobot MCP Services Installation Script for Windows

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

# Create MCP services directory if it doesn't exist
$McpDir = "C:\Program Files\Cryptobot\services\mcp"
Log "Creating MCP services directory at $McpDir"
New-Item -ItemType Directory -Force -Path $McpDir | Out-Null

# Copy MCP router
Log "Copying MCP router..."
Copy-Item -Path ".\services\mcp\mcp_router.py" -Destination "$McpDir\" -Force

# Install MCP services
Log "Installing MCP services..."

# Exchange Gateway
Log "Installing Exchange Gateway MCP service..."
$ExchangeGatewayDir = "$McpDir\exchange-gateway"
New-Item -ItemType Directory -Force -Path $ExchangeGatewayDir | Out-Null
Copy-Item -Path ".\services\mcp\exchange-gateway\*" -Destination $ExchangeGatewayDir -Recurse -Force

# Market Data
Log "Installing Market Data MCP service..."
$MarketDataDir = "$McpDir\market-data"
New-Item -ItemType Directory -Force -Path $MarketDataDir | Out-Null
Copy-Item -Path ".\services\mcp\market-data\*" -Destination $MarketDataDir -Recurse -Force

# Order Execution
Log "Installing Order Execution MCP service..."
$OrderExecutionDir = "$McpDir\order-execution"
New-Item -ItemType Directory -Force -Path $OrderExecutionDir | Out-Null
Copy-Item -Path ".\services\mcp\order-execution\*" -Destination $OrderExecutionDir -Recurse -Force

# Paper Trading
Log "Installing Paper Trading MCP service..."
$PaperTradingDir = "$McpDir\paper-trading"
New-Item -ItemType Directory -Force -Path $PaperTradingDir | Out-Null
Copy-Item -Path ".\services\mcp\paper-trading\*" -Destination $PaperTradingDir -Recurse -Force

# Portfolio Management
Log "Installing Portfolio Management MCP service..."
$PortfolioMgmtDir = "$McpDir\portfolio-management"
New-Item -ItemType Directory -Force -Path $PortfolioMgmtDir | Out-Null
Copy-Item -Path ".\services\mcp\portfolio-management\*" -Destination $PortfolioMgmtDir -Recurse -Force

# Reporting
Log "Installing Reporting MCP service..."
$ReportingDir = "$McpDir\reporting"
New-Item -ItemType Directory -Force -Path $ReportingDir | Out-Null
Copy-Item -Path ".\services\mcp\reporting\*" -Destination $ReportingDir -Recurse -Force

# Risk Management
Log "Installing Risk Management MCP service..."
$RiskMgmtDir = "$McpDir\risk-management"
New-Item -ItemType Directory -Force -Path $RiskMgmtDir | Out-Null
Copy-Item -Path ".\services\mcp\risk-management\*" -Destination $RiskMgmtDir -Recurse -Force

# Strategy Execution
Log "Installing Strategy Execution MCP service..."
$StrategyExecDir = "$McpDir\strategy-execution"
New-Item -ItemType Directory -Force -Path $StrategyExecDir | Out-Null
Copy-Item -Path ".\services\mcp\strategy-execution\*" -Destination $StrategyExecDir -Recurse -Force

# Install dependencies for each MCP service
Log "Installing dependencies for MCP services..."

# Check if we're in a virtual environment
if (-not $env:VIRTUAL_ENV) {
    Log "Warning: Not running in a virtual environment. It's recommended to activate the virtual environment first."
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        Log "Please activate the virtual environment and try again."
        exit 1
    }
}

# Install dependencies for Exchange Gateway
if (Test-Path "$ExchangeGatewayDir\requirements.txt") {
    Log "Installing Exchange Gateway dependencies..."
    pip install -r "$ExchangeGatewayDir\requirements.txt"
}

# Install dependencies for Paper Trading
if (Test-Path "$PaperTradingDir\requirements.txt") {
    Log "Installing Paper Trading dependencies..."
    pip install -r "$PaperTradingDir\requirements.txt"
}

# Install common dependencies for other MCP services
Log "Installing common dependencies for MCP services..."
pip install pydantic fastapi uvicorn requests

# Create MCP configuration
Log "Setting up MCP services configuration..."
$ConfigDir = "C:\ProgramData\Cryptobot\mcp"
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

# Check if config file exists from Phase 3
if (Test-Path ".\config\mcp_services_config.json") {
    Copy-Item -Path ".\config\mcp_services_config.json" -Destination "$ConfigDir\config.json" -Force
    Log "Copied configuration from Phase 3 setup."
}
else {
    Log "Warning: Configuration file from Phase 3 not found. Using default configuration."
    # Create a default config file
    $defaultConfig = @"
{
    "mcp_router": {
        "host": "0.0.0.0",
        "port": 8010,
        "log_level": "info"
    },
    "exchange_gateway": {
        "host": "0.0.0.0",
        "port": 8011,
        "log_level": "info",
        "supported_exchanges": ["binance", "kraken", "coinbase"],
        "api_keys_path": "C:\\ProgramData\\Cryptobot\\mcp\\api_keys.json"
    },
    "paper_trading": {
        "host": "0.0.0.0",
        "port": 8012,
        "log_level": "info",
        "initial_balance": 10000,
        "fee_rate": 0.001
    },
    "order_execution": {
        "retry_attempts": 3,
        "retry_delay": 2,
        "timeout": 30
    },
    "risk_management": {
        "max_open_trades": 5,
        "max_open_trades_per_pair": 1,
        "max_daily_drawdown_percent": 5,
        "stop_loss_percent": 2.5
    },
    "portfolio_management": {
        "rebalance_frequency": "daily",
        "target_allocation": {
            "BTC": 0.5,
            "ETH": 0.3,
            "other": 0.2
        }
    },
    "reporting": {
        "report_directory": "C:\\ProgramData\\Cryptobot\\reports",
        "report_formats": ["json", "csv", "html"]
    }
}
"@
    $defaultConfig | Out-File -FilePath "$ConfigDir\config.json" -Encoding utf8
    Log "Created default configuration. Please update with secure values."
    
    # Create a default API keys file
    $apiKeysConfig = @"
{
    "binance": {
        "api_key": "YOUR_BINANCE_API_KEY",
        "api_secret": "YOUR_BINANCE_API_SECRET"
    },
    "kraken": {
        "api_key": "YOUR_KRAKEN_API_KEY",
        "api_secret": "YOUR_KRAKEN_API_SECRET"
    },
    "coinbase": {
        "api_key": "YOUR_COINBASE_API_KEY",
        "api_secret": "YOUR_COINBASE_API_SECRET",
        "passphrase": "YOUR_COINBASE_PASSPHRASE"
    }
}
"@
    $apiKeysConfig | Out-File -FilePath "$ConfigDir\api_keys.json" -Encoding utf8
    Log "Created default API keys file. Please update with your actual API keys."
    
    # Set secure permissions on API keys file
    $acl = Get-Acl "$ConfigDir\api_keys.json"
    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM", "FullControl", "Allow")
    $acl.SetAccessRule($accessRule)
    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "Allow")
    $acl.SetAccessRule($accessRule)
    Set-Acl "$ConfigDir\api_keys.json" $acl
}

# Create a symbolic link to the configuration (Windows uses junction points)
cmd /c mklink /J "$McpDir\config.json" "$ConfigDir\config.json"

# Create reports directory
$ReportsDir = "C:\ProgramData\Cryptobot\reports"
New-Item -ItemType Directory -Force -Path $ReportsDir | Out-Null

# Set up Windows services
Log "Setting up Windows services for MCP services..."

# Check if NSSM (Non-Sucking Service Manager) is installed
$nssmPath = "C:\Program Files\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    Log "NSSM (Non-Sucking Service Manager) is required to create Windows services."
    Log "Downloading NSSM..."
    
    # Create a temporary directory
    $tempDir = [System.IO.Path]::GetTempPath() + [System.Guid]::NewGuid().ToString()
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    
    # Download NSSM
    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $nssmZip = "$tempDir\nssm.zip"
    Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
    
    # Extract NSSM
    Expand-Archive -Path $nssmZip -DestinationPath $tempDir
    
    # Create NSSM directory
    New-Item -ItemType Directory -Force -Path "C:\Program Files\nssm" | Out-Null
    
    # Copy NSSM executable
    Copy-Item -Path "$tempDir\nssm-2.24\win64\nssm.exe" -Destination $nssmPath -Force
    
    # Clean up
    Remove-Item -Path $tempDir -Recurse -Force
    
    Log "NSSM has been installed."
}

# Create batch files to run the services
$mcpRouterBatch = "$McpDir\run_mcp_router.bat"
@"
@echo off
cd /d "%~dp0"
set PYTHONPATH=%PYTHONPATH%;%CD%
python -m uvicorn mcp_router:app --host 0.0.0.0 --port 8010
"@ | Out-File -FilePath $mcpRouterBatch -Encoding ascii

$exchangeGatewayBatch = "$ExchangeGatewayDir\run_service.bat"
@"
@echo off
cd /d "%~dp0"
set PYTHONPATH=%PYTHONPATH%;%CD%;%CD%\..
python main.py
"@ | Out-File -FilePath $exchangeGatewayBatch -Encoding ascii

$paperTradingBatch = "$PaperTradingDir\run_service.bat"
@"
@echo off
cd /d "%~dp0"
set PYTHONPATH=%PYTHONPATH%;%CD%;%CD%\..
python main.py
"@ | Out-File -FilePath $paperTradingBatch -Encoding ascii

# Create the Windows services using NSSM
# MCP Router Service
& $nssmPath install CryptobotMcpRouter "$mcpRouterBatch"
& $nssmPath set CryptobotMcpRouter DisplayName "Cryptobot MCP Router Service"
& $nssmPath set CryptobotMcpRouter Description "MCP Router service for Cryptobot"
& $nssmPath set CryptobotMcpRouter AppDirectory "$McpDir"
& $nssmPath set CryptobotMcpRouter AppStdout "$McpDir\mcp_router.log"
& $nssmPath set CryptobotMcpRouter AppStderr "$McpDir\mcp_router.err"
& $nssmPath set CryptobotMcpRouter Start SERVICE_AUTO_START
& $nssmPath set CryptobotMcpRouter ObjectName LocalSystem

# Set service dependencies
& $nssmPath set CryptobotMcpRouter DependOnService CryptobotAuth CryptobotStrategy CryptobotData CryptobotTrade

# Exchange Gateway Service
& $nssmPath install CryptobotExchangeGateway "$exchangeGatewayBatch"
& $nssmPath set CryptobotExchangeGateway DisplayName "Cryptobot Exchange Gateway Service"
& $nssmPath set CryptobotExchangeGateway Description "Exchange Gateway MCP service for Cryptobot"
& $nssmPath set CryptobotExchangeGateway AppDirectory "$ExchangeGatewayDir"
& $nssmPath set CryptobotExchangeGateway AppStdout "$ExchangeGatewayDir\service.log"
& $nssmPath set CryptobotExchangeGateway AppStderr "$ExchangeGatewayDir\service.err"
& $nssmPath set CryptobotExchangeGateway Start SERVICE_AUTO_START
& $nssmPath set CryptobotExchangeGateway ObjectName LocalSystem

# Set service dependencies
& $nssmPath set CryptobotExchangeGateway DependOnService CryptobotMcpRouter

# Paper Trading Service
& $nssmPath install CryptobotPaperTrading "$paperTradingBatch"
& $nssmPath set CryptobotPaperTrading DisplayName "Cryptobot Paper Trading Service"
& $nssmPath set CryptobotPaperTrading Description "Paper Trading MCP service for Cryptobot"
& $nssmPath set CryptobotPaperTrading AppDirectory "$PaperTradingDir"
& $nssmPath set CryptobotPaperTrading AppStdout "$PaperTradingDir\service.log"
& $nssmPath set CryptobotPaperTrading AppStderr "$PaperTradingDir\service.err"
& $nssmPath set CryptobotPaperTrading Start SERVICE_AUTO_START
& $nssmPath set CryptobotPaperTrading ObjectName LocalSystem

# Set service dependencies
& $nssmPath set CryptobotPaperTrading DependOnService CryptobotMcpRouter

Log "MCP services have been installed and configured as Windows services."
Log "To start the services, run:"
Log "  Start-Service CryptobotMcpRouter"
Log "  Start-Service CryptobotExchangeGateway"
Log "  Start-Service CryptobotPaperTrading"

Log "MCP services installation completed successfully!"
Log "You can manually start the services by running:"
Log "  $mcpRouterBatch"
Log "  $exchangeGatewayBatch"
Log "  $paperTradingBatch"

exit 0