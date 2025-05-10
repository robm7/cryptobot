# Cryptobot Environment Variables Setup Script for Windows
# This script sets up environment variables for non-Docker deployment

# Function to display messages
function Log {
    param (
        [string]$Message
    )
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
}

# Create .env file in the project root
function Create-EnvFile {
    param (
        [string]$FilePath,
        [hashtable]$Variables
    )
    
    if (Test-Path $FilePath) {
        Log "Backing up existing .env file to $FilePath.bak"
        Copy-Item -Path $FilePath -Destination "$FilePath.bak" -Force
    }
    
    Log "Creating $FilePath"
    $content = ""
    foreach ($key in $Variables.Keys) {
        $content += "$key=$($Variables[$key])`n"
    }
    
    Set-Content -Path $FilePath -Value $content -Force
    Log "Environment variables written to $FilePath"
}

# Display welcome message
Log "Setting up environment variables for Cryptobot services..."

# Get project root directory
$projectRoot = $PSScriptRoot | Split-Path | Split-Path

# Common variables
$commonVars = @{
    "ENVIRONMENT" = "development"
    "DEBUG" = "true"
    "LOG_LEVEL" = "INFO"
}

# Create service-specific .env files
# Auth Service
$authVars = $commonVars.Clone()
$authVars["SERVER_HOST"] = "0.0.0.0"
$authVars["SERVER_PORT"] = "8000"
$authVars["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/cryptobot_auth"
$authVars["SECRET_KEY"] = "dev_secret_key_change_in_production"
$authVars["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
$authVars["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"

Create-EnvFile -FilePath "$projectRoot\auth\.env" -Variables $authVars

# Strategy Service
$strategyVars = $commonVars.Clone()
$strategyVars["SERVER_HOST"] = "0.0.0.0"
$strategyVars["SERVER_PORT"] = "8000"
$strategyVars["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/cryptobot_strategy"
$strategyVars["AUTH_SERVICE_URL"] = "http://localhost:8000"
$strategyVars["SECRET_KEY"] = "dev_secret_key_change_in_production"
$strategyVars["TOKEN_CACHE_TTL"] = "60"
$strategyVars["ADMIN_ROLE"] = "admin"
$strategyVars["TRADER_ROLE"] = "trader"
$strategyVars["VIEWER_ROLE"] = "viewer"

Create-EnvFile -FilePath "$projectRoot\strategy\.env" -Variables $strategyVars

# Trade Service
$tradeVars = $commonVars.Clone()
$tradeVars["SERVER_HOST"] = "0.0.0.0"
$tradeVars["SERVER_PORT"] = "8000"
$tradeVars["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/cryptobot_trade"
$tradeVars["AUTH_SERVICE_URL"] = "http://localhost:8000"
$tradeVars["TRADE_API_KEY"] = "dev_trade_api_key_change_in_production"
$tradeVars["EXCHANGE_API_KEY"] = "your_exchange_api_key"
$tradeVars["EXCHANGE_API_SECRET"] = "your_exchange_api_secret"
$tradeVars["EXCHANGE_PASSPHRASE"] = ""
$tradeVars["EXCHANGE_SANDBOX"] = "true"

Create-EnvFile -FilePath "$projectRoot\trade\.env" -Variables $tradeVars

# Backtest Service
$backtestVars = $commonVars.Clone()
$backtestVars["SERVER_HOST"] = "0.0.0.0"
$backtestVars["SERVER_PORT"] = "8000"
$backtestVars["APP_NAME"] = "Backtest Service"
$backtestVars["MAX_CONCURRENT_BACKTESTS"] = "5"
$backtestVars["RESULTS_TTL_DAYS"] = "7"
$backtestVars["DATABASE_URL"] = "sqlite:///./backtest.db"
$backtestVars["DATA_SERVICE_URL"] = "http://localhost:8001"
$backtestVars["STRATEGY_SERVICE_URL"] = "http://localhost:8000"

Create-EnvFile -FilePath "$projectRoot\backtest\.env" -Variables $backtestVars

# Data Service
$dataVars = $commonVars.Clone()
$dataVars["HOST"] = "0.0.0.0"
$dataVars["PORT"] = "8001"
$dataVars["WORKERS"] = "1"
$dataVars["DATA_CACHE_TTL"] = "300"
$dataVars["EXCHANGES"] = "binance,kraken,coinbase"
$dataVars["REDIS_HOST"] = "localhost"
$dataVars["REDIS_PORT"] = "6379"
$dataVars["REDIS_DB"] = "0"
$dataVars["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/cryptobot_data"

Create-EnvFile -FilePath "$projectRoot\data\.env" -Variables $dataVars

# Create a global .env file in the project root
$globalVars = @{
    "ENVIRONMENT" = "development"
    "DEBUG" = "true"
    "LOG_LEVEL" = "INFO"
    "AUTH_SERVICE_URL" = "http://localhost:8000"
    "STRATEGY_SERVICE_URL" = "http://localhost:8000"
    "TRADE_SERVICE_URL" = "http://localhost:8000"
    "BACKTEST_SERVICE_URL" = "http://localhost:8000"
    "DATA_SERVICE_URL" = "http://localhost:8001"
}

Create-EnvFile -FilePath "$projectRoot\.env" -Variables $globalVars

Log "Environment variables setup completed successfully!"
Log "Note: For production use, please update the sensitive values in the .env files."

exit 0