# Cryptobot Master Service Installation Script for Windows
# This script orchestrates the installation of all Cryptobot services

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

# Display welcome message
Log "Welcome to the Cryptobot Service Installation!"
Log "This script will install and configure all Cryptobot services."
Log "The installation process includes:"
Log "1. Core services (auth, strategy, backtest, trade, data)"
Log "2. MCP services"
Log "3. Service integration and communication setup"
Log ""
Log "The installation process may take several minutes to complete."
Log ""

Write-Host "Press Enter to continue or Ctrl+C to cancel..." -NoNewline
$null = Read-Host

# Create a directory for logs
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# Step 1: Install Auth Service
Log "Step 1: Installing Auth Service"
Log "Running install_auth.ps1..."
$authOutput = & "$PSScriptRoot\install_auth.ps1" 2>&1
$authOutput | Out-File -FilePath "logs\install_auth.log"
$authOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Auth service installation failed. Please check logs\install_auth.log for details."
    exit 1
}

Log "Auth service installation completed successfully!"

# Step 2: Install Data Service
Log "Step 2: Installing Data Service"
Log "Running install_data.ps1..."
$dataOutput = & "$PSScriptRoot\install_data.ps1" 2>&1
$dataOutput | Out-File -FilePath "logs\install_data.log"
$dataOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Data service installation failed. Please check logs\install_data.log for details."
    exit 1
}

Log "Data service installation completed successfully!"

# Step 3: Install Strategy Service
Log "Step 3: Installing Strategy Service"
Log "Running install_strategy.ps1..."
$strategyOutput = & "$PSScriptRoot\install_strategy.ps1" 2>&1
$strategyOutput | Out-File -FilePath "logs\install_strategy.log"
$strategyOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Strategy service installation failed. Please check logs\install_strategy.log for details."
    exit 1
}

Log "Strategy service installation completed successfully!"

# Step 4: Install Backtest Service
Log "Step 4: Installing Backtest Service"
Log "Running install_backtest.ps1..."
$backtestOutput = & "$PSScriptRoot\install_backtest.ps1" 2>&1
$backtestOutput | Out-File -FilePath "logs\install_backtest.log"
$backtestOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Backtest service installation failed. Please check logs\install_backtest.log for details."
    exit 1
}

Log "Backtest service installation completed successfully!"

# Step 5: Install Trade Service
Log "Step 5: Installing Trade Service"
Log "Running install_trade.ps1..."
$tradeOutput = & "$PSScriptRoot\install_trade.ps1" 2>&1
$tradeOutput | Out-File -FilePath "logs\install_trade.log"
$tradeOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Trade service installation failed. Please check logs\install_trade.log for details."
    exit 1
}

Log "Trade service installation completed successfully!"

# Step 6: Install MCP Services
Log "Step 6: Installing MCP Services"
Log "Running install_mcp_services.ps1..."
$mcpOutput = & "$PSScriptRoot\install_mcp_services.ps1" 2>&1
$mcpOutput | Out-File -FilePath "logs\install_mcp_services.log"
$mcpOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: MCP services installation failed. Please check logs\install_mcp_services.log for details."
    exit 1
}

Log "MCP services installation completed successfully!"

# Step 7: Setup Service Integration
Log "Step 7: Setting up Service Integration"
Log "Running setup_service_integration.ps1..."
$integrationOutput = & "$PSScriptRoot\setup_service_integration.ps1" 2>&1
$integrationOutput | Out-File -FilePath "logs\setup_service_integration.log"
$integrationOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Service integration setup failed. Please check logs\setup_service_integration.log for details."
    exit 1
}

Log "Service integration setup completed successfully!"

# Final steps and verification
Log "Verifying installation..."

# Check if all service directories exist
$serviceDirs = @(
    "C:\Program Files\Cryptobot\services\auth",
    "C:\Program Files\Cryptobot\services\strategy",
    "C:\Program Files\Cryptobot\services\backtest",
    "C:\Program Files\Cryptobot\services\trade",
    "C:\Program Files\Cryptobot\services\data",
    "C:\Program Files\Cryptobot\services\mcp"
)

foreach ($dir in $serviceDirs) {
    if (Test-Path $dir) {
        Log "Service directory $dir exists."
    } else {
        Log "Warning: Service directory $dir does not exist."
    }
}

# Check if all configuration files exist
$configFiles = @(
    "C:\ProgramData\Cryptobot\auth\config.json",
    "C:\ProgramData\Cryptobot\strategy\config.json",
    "C:\ProgramData\Cryptobot\backtest\config.json",
    "C:\ProgramData\Cryptobot\trade\config.json",
    "C:\ProgramData\Cryptobot\data\config.json",
    "C:\ProgramData\Cryptobot\mcp\config.json",
    "C:\ProgramData\Cryptobot\service_discovery.json"
)

foreach ($file in $configFiles) {
    if (Test-Path $file) {
        Log "Configuration file $file exists."
    } else {
        Log "Warning: Configuration file $file does not exist."
    }
}

# Check if Windows services are installed
$windowsServices = @(
    "CryptobotAuth",
    "CryptobotStrategy",
    "CryptobotBacktest",
    "CryptobotTrade",
    "CryptobotData",
    "CryptobotMcpRouter",
    "CryptobotExchangeGateway",
    "CryptobotPaperTrading"
)

foreach ($service in $windowsServices) {
    if (Get-Service -Name $service -ErrorAction SilentlyContinue) {
        Log "Windows service $service is installed."
    } else {
        Log "Warning: Windows service $service is not installed."
    }
}

Log "Service installation completed successfully!"
Log ""
Log "To start all services, you can use the following commands:"
Log "  Start-Service CryptobotAuth"
Log "  Start-Service CryptobotData"
Log "  Start-Service CryptobotStrategy"
Log "  Start-Service CryptobotBacktest"
Log "  Start-Service CryptobotTrade"
Log "  Start-Service CryptobotMcpRouter"
Log "  Start-Service CryptobotExchangeGateway"
Log "  Start-Service CryptobotPaperTrading"
Log ""
Log "Or use the restart script:"
Log "  C:\Program Files\Cryptobot\scripts\restart_services.ps1"
Log ""
Log "To check the health of all services, run:"
Log "  C:\Program Files\Cryptobot\scripts\health_check.ps1"
Log ""
Log "Thank you for installing Cryptobot services!"

exit 0