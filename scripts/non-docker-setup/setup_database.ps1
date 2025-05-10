# Cryptobot PostgreSQL Database Setup Script for Windows
# This script installs and configures PostgreSQL for the Cryptobot application

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

Log "Starting PostgreSQL database setup for Cryptobot..."

# Load environment variables from .env file if it exists
if (Test-Path .env) {
    Log "Loading environment variables from .env file..."
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^#][^=]*)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Variable -Name $key -Value $value
        }
    }
} else {
    Log "Warning: .env file not found. Using default values."
    # Set default values
    $DB_HOST = "localhost"
    $DB_PORT = "5432"
    $DB_USER = "cryptobot"
    $DB_PASSWORD = "changeme"
    $DB_NAME = "cryptobot"
}

# Check if Chocolatey is installed
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Log "Error: Chocolatey is not installed. Please run setup_base_system.ps1 first."
    exit 1
}

# Install PostgreSQL
Log "Installing PostgreSQL..."
choco install -y postgresql --params "/Password:postgres /Port:$DB_PORT"

# Refresh environment variables
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

# Wait for PostgreSQL to start
Log "Waiting for PostgreSQL to start..."
Start-Sleep -Seconds 10

# Create database and user
Log "Creating database and user..."
$pgPassword = "postgres"
$env:PGPASSWORD = $pgPassword

# Create user
$createUserCmd = "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
$createUserResult = & psql -h localhost -U postgres -c $createUserCmd 2>&1
if ($LASTEXITCODE -ne 0) {
    if ($createUserResult -match "already exists") {
        Log "User $DB_USER already exists, continuing..."
    } else {
        Log "Error creating user: $createUserResult"
        exit 1
    }
}

# Create database
$createDbCmd = "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
$createDbResult = & psql -h localhost -U postgres -c $createDbCmd 2>&1
if ($LASTEXITCODE -ne 0) {
    if ($createDbResult -match "already exists") {
        Log "Database $DB_NAME already exists, continuing..."
    } else {
        Log "Error creating database: $createDbResult"
        exit 1
    }
}

# Grant privileges
$grantCmd = "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
$grantResult = & psql -h localhost -U postgres -c $grantCmd 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Error granting privileges: $grantResult"
    exit 1
}

# Create database schema
Log "Creating database schema..."
$schemaFile = "db_schema.sql"
$schemaContent = @"
-- Cryptobot Database Schema

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE
);

-- API Keys Table
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    exchange VARCHAR(50) NOT NULL,
    api_key VARCHAR(255) NOT NULL,
    api_secret VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id, exchange)
);

-- Strategies Table
CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id, name)
);

-- Trades Table
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE SET NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    order_id VARCHAR(100),
    order_type VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8),
    executed_price DECIMAL(18, 8),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP WITH TIME ZONE,
    profit_loss DECIMAL(18, 8)
);

-- Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);
"@

Set-Content -Path $schemaFile -Value $schemaContent

# Apply database schema
$env:PGPASSWORD = $DB_PASSWORD
$applySchemaResult = & psql -h localhost -U $DB_USER -d $DB_NAME -f $schemaFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "Error applying schema: $applySchemaResult"
    exit 1
}

# Clean up
Remove-Item $schemaFile

Log "PostgreSQL database setup completed successfully!"
Log "Database: $DB_NAME"
Log "User: $DB_USER"
Log "Password: $DB_PASSWORD"
Log "Host: $DB_HOST"
Log "Port: $DB_PORT"

# Add PostgreSQL bin directory to PATH if not already there
$pgBinPath = "C:\Program Files\PostgreSQL\15\bin"
if (-not $env:Path.Contains($pgBinPath)) {
    Log "Adding PostgreSQL bin directory to PATH..."
    [Environment]::SetEnvironmentVariable("Path", $env:Path + ";$pgBinPath", [EnvironmentVariableTarget]::Machine)
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

exit 0