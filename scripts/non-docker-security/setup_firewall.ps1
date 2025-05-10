# Cryptobot Firewall Configuration Script for Windows
# This script configures Windows Firewall rules to protect the Cryptobot application

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

Log "Starting Windows Firewall configuration for Cryptobot..."

# Load environment variables from .env file if it exists
if (Test-Path ".env") {
    Log "Loading environment variables from .env file..."
    $envContent = Get-Content ".env" -Raw
    $envLines = $envContent -split "`n" | Where-Object { $_ -match '^\s*[^#]' }
    $envVars = @{}
    foreach ($line in $envLines) {
        if ($line -match '^\s*([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            $envVars[$key] = $value
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
} else {
    Log "Warning: .env file not found. Using default values."
    # Set default values
    $envVars = @{
        "AUTH_SERVICE_PORT" = "8000"
        "STRATEGY_SERVICE_PORT" = "8010"
        "BACKTEST_SERVICE_PORT" = "8020"
        "TRADE_SERVICE_PORT" = "8030"
        "DATA_SERVICE_PORT" = "8001"
        "DB_PORT" = "5432"
        "REDIS_PORT" = "6379"
    }
}

# Extract service ports from environment variables
$authPort = $envVars["AUTH_SERVICE_PORT"]
$strategyPort = $envVars["STRATEGY_SERVICE_PORT"]
$backtestPort = $envVars["BACKTEST_SERVICE_PORT"]
$tradePort = $envVars["TRADE_SERVICE_PORT"]
$dataPort = $envVars["DATA_SERVICE_PORT"]
$dbPort = $envVars["DB_PORT"]
$redisPort = $envVars["REDIS_PORT"]

# Enable Windows Firewall
Log "Ensuring Windows Firewall is enabled..."
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True

# Create a firewall rule group for Cryptobot
$ruleGroupName = "Cryptobot"
Log "Creating firewall rule group: $ruleGroupName"

# Remove existing rules in the group if they exist
Log "Removing any existing Cryptobot firewall rules..."
Get-NetFirewallRule -DisplayGroup $ruleGroupName -ErrorAction SilentlyContinue | Remove-NetFirewallRule

# Allow service ports
Log "Creating inbound rules for Cryptobot service ports..."

# Auth Service
New-NetFirewallRule -DisplayName "Cryptobot Auth Service" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort $authPort `
    -Action Allow `
    -Profile Domain,Private `
    -DisplayGroup $ruleGroupName `
    -Description "Allow inbound traffic to Cryptobot Auth Service"

# Strategy Service
New-NetFirewallRule -DisplayName "Cryptobot Strategy Service" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort $strategyPort `
    -Action Allow `
    -Profile Domain,Private `
    -DisplayGroup $ruleGroupName `
    -Description "Allow inbound traffic to Cryptobot Strategy Service"

# Backtest Service
New-NetFirewallRule -DisplayName "Cryptobot Backtest Service" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort $backtestPort `
    -Action Allow `
    -Profile Domain,Private `
    -DisplayGroup $ruleGroupName `
    -Description "Allow inbound traffic to Cryptobot Backtest Service"

# Trade Service
New-NetFirewallRule -DisplayName "Cryptobot Trade Service" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort $tradePort `
    -Action Allow `
    -Profile Domain,Private `
    -DisplayGroup $ruleGroupName `
    -Description "Allow inbound traffic to Cryptobot Trade Service"

# Data Service
New-NetFirewallRule -DisplayName "Cryptobot Data Service" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort $dataPort `
    -Action Allow `
    -Profile Domain,Private `
    -DisplayGroup $ruleGroupName `
    -Description "Allow inbound traffic to Cryptobot Data Service"

# Web Interface (default: 3000)
New-NetFirewallRule -DisplayName "Cryptobot Web Interface" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 3000 `
    -Action Allow `
    -Profile Domain,Private `
    -DisplayGroup $ruleGroupName `
    -Description "Allow inbound traffic to Cryptobot Web Interface"

# Restrict database and Redis access to localhost only
Log "Restricting database and Redis access to localhost only..."

# Block external access to PostgreSQL
New-NetFirewallRule -DisplayName "Block External PostgreSQL" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort $dbPort `
    -RemoteAddress Any `
    -Action Block `
    -Profile Domain,Private,Public `
    -DisplayGroup $ruleGroupName `
    -Description "Block external access to PostgreSQL"

# Allow localhost access to PostgreSQL
New-NetFirewallRule -DisplayName "Allow Localhost PostgreSQL" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort $dbPort `
    -RemoteAddress LocalSubnet,127.0.0.1 `
    -Action Allow `
    -Profile Domain,Private,Public `
    -DisplayGroup $ruleGroupName `
    -Description "Allow localhost access to PostgreSQL"

# Block external access to Redis
New-NetFirewallRule -DisplayName "Block External Redis" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort $redisPort `
    -RemoteAddress Any `
    -Action Block `
    -Profile Domain,Private,Public `
    -DisplayGroup $ruleGroupName `
    -Description "Block external access to Redis"

# Allow localhost access to Redis
New-NetFirewallRule -DisplayName "Allow Localhost Redis" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort $redisPort `
    -RemoteAddress LocalSubnet,127.0.0.1 `
    -Action Allow `
    -Profile Domain,Private,Public `
    -DisplayGroup $ruleGroupName `
    -Description "Allow localhost access to Redis"

# Block outbound connections to suspicious ports
Log "Blocking outbound connections to suspicious ports..."
$suspiciousPorts = @(25, 465, 587, 2525, 1433, 3306, 5432, 6379, 27017, 11211)
New-NetFirewallRule -DisplayName "Block Suspicious Outbound" `
    -Direction Outbound `
    -Protocol TCP `
    -RemotePort $suspiciousPorts `
    -Action Block `
    -Profile Domain,Private,Public `
    -DisplayGroup $ruleGroupName `
    -Description "Block outbound connections to suspicious ports"

# Allow outbound connections to necessary services
Log "Allowing outbound connections to necessary services..."
New-NetFirewallRule -DisplayName "Allow Cryptobot Outbound" `
    -Direction Outbound `
    -Protocol TCP `
    -RemotePort 80,443 `
    -Action Allow `
    -Profile Domain,Private,Public `
    -DisplayGroup $ruleGroupName `
    -Description "Allow outbound connections to HTTP/HTTPS services"

# Enable logging for blocked connections
Log "Enabling logging for blocked connections..."
Set-NetFirewallProfile -Profile Domain,Private,Public -LogBlocked True -LogMaxSize 4096

# Display summary of created rules
Log "Displaying summary of created firewall rules..."
Get-NetFirewallRule -DisplayGroup $ruleGroupName | Format-Table -Property DisplayName, Enabled, Direction, Action

Log "Windows Firewall configuration completed successfully!"
exit 0