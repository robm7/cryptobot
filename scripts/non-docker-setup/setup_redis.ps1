# Cryptobot Redis Setup Script for Windows
# This script installs and configures Redis for the Cryptobot application

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

Log "Starting Redis setup for Cryptobot..."

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
    $REDIS_HOST = "localhost"
    $REDIS_PORT = "6379"
    $REDIS_PASSWORD = ""
}

# Check if Chocolatey is installed
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Log "Error: Chocolatey is not installed. Please run setup_base_system.ps1 first."
    exit 1
}

# Install Redis
Log "Installing Redis..."
choco install -y redis-64

# Refresh environment variables
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

# Configure Redis
Log "Configuring Redis..."

# Redis configuration directory
$redisDir = "C:\Program Files\Redis"
$redisConfFile = "$redisDir\redis.windows.conf"

# Backup original configuration
if (Test-Path $redisConfFile) {
    Copy-Item $redisConfFile "$redisConfFile.bak"
}

# Update Redis configuration
if (Test-Path $redisConfFile) {
    $redisConf = Get-Content $redisConfFile

    # Set Redis port
    $redisConf = $redisConf -replace "port 6379", "port $REDIS_PORT"

    # Set Redis password if provided
    if ($REDIS_PASSWORD) {
        Log "Setting Redis password..."
        $redisConf = $redisConf -replace "# requirepass foobared", "requirepass $REDIS_PASSWORD"
    }

    # Save updated configuration
    Set-Content -Path $redisConfFile -Value $redisConf
} else {
    Log "Warning: Redis configuration file not found at $redisConfFile"
}

# Install Redis as a Windows service
Log "Installing Redis as a Windows service..."
$redisServiceExists = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
if (-not $redisServiceExists) {
    $redisServerExe = "$redisDir\redis-server.exe"
    if (Test-Path $redisServerExe) {
        & $redisServerExe --service-install $redisConfFile --service-name Redis
        if ($LASTEXITCODE -ne 0) {
            Log "Error: Failed to install Redis as a service."
            exit 1
        }
    } else {
        Log "Error: Redis server executable not found at $redisServerExe"
        exit 1
    }
} else {
    Log "Redis service already exists."
}

# Start Redis service
Log "Starting Redis service..."
Start-Service Redis
if ((Get-Service Redis).Status -ne 'Running') {
    Log "Error: Failed to start Redis service."
    exit 1
}

# Set Redis service to start automatically
Set-Service -Name Redis -StartupType Automatic

# Wait for Redis to start
Log "Waiting for Redis to start..."
Start-Sleep -Seconds 3

# Test Redis connection
Log "Testing Redis connection..."
$redisCliExe = "$redisDir\redis-cli.exe"
if (Test-Path $redisCliExe) {
    if ($REDIS_PASSWORD) {
        $pingResult = & $redisCliExe -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping
    } else {
        $pingResult = & $redisCliExe -h $REDIS_HOST -p $REDIS_PORT ping
    }
    
    if ($pingResult -eq "PONG") {
        Log "Redis connection successful!"
    } else {
        Log "Error: Could not connect to Redis. Please check your configuration."
        exit 1
    }
} else {
    Log "Warning: redis-cli not found at $redisCliExe. Could not test Redis connection."
}

Log "Redis setup completed successfully!"
Log "Redis Host: $REDIS_HOST"
Log "Redis Port: $REDIS_PORT"
if ($REDIS_PASSWORD) {
    Log "Redis Password: $REDIS_PASSWORD"
} else {
    Log "Redis Password: Not set"
}

# Add Redis directory to PATH if not already there
if (-not $env:Path.Contains($redisDir)) {
    Log "Adding Redis directory to PATH..."
    [Environment]::SetEnvironmentVariable("Path", $env:Path + ";$redisDir", [EnvironmentVariableTarget]::Machine)
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

exit 0