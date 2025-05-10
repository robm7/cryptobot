# Cryptobot Security Configuration Script for Windows
# This script applies security hardening configurations to the Cryptobot application

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

Log "Starting security configuration for Cryptobot..."

# Create security directory if it doesn't exist
New-Item -ItemType Directory -Force -Path "config\security" | Out-Null

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
        "DB_HOST" = "localhost"
        "DB_PORT" = "5432"
        "DB_USER" = "cryptobot"
        "DB_PASSWORD" = "changeme"
        "DB_NAME" = "cryptobot"
        "REDIS_HOST" = "localhost"
        "REDIS_PORT" = "6379"
        "AUTH_SERVICE_PORT" = "8000"
        "STRATEGY_SERVICE_PORT" = "8010"
        "BACKTEST_SERVICE_PORT" = "8020"
        "TRADE_SERVICE_PORT" = "8030"
        "DATA_SERVICE_PORT" = "8001"
        "LOG_LEVEL" = "INFO"
        "LOG_DIR" = "./logs"
    }
}

# Generate strong random secret key for JWT tokens
Log "Generating secure JWT secret key..."
$JwtSecret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
Log "JWT secret key generated"

# Generate strong random secret key for password reset tokens
Log "Generating secure password reset secret key..."
$ResetSecret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
Log "Password reset secret key generated"

# Update .env file with secure keys
Log "Updating environment configuration with secure keys..."
$envContent = if (Test-Path ".env") { Get-Content ".env" -Raw } else { "" }
$envLines = $envContent -split "`n"
$updatedEnvLines = @()
$jwtSecretAdded = $false
$resetSecretAdded = $false

foreach ($line in $envLines) {
    if ($line -match '^JWT_SECRET_KEY=') {
        $updatedEnvLines += "JWT_SECRET_KEY=$JwtSecret"
        $jwtSecretAdded = $true
    } elseif ($line -match '^RESET_SECRET_KEY=') {
        $updatedEnvLines += "RESET_SECRET_KEY=$ResetSecret"
        $resetSecretAdded = $true
    } else {
        $updatedEnvLines += $line
    }
}

if (-not $jwtSecretAdded) {
    $updatedEnvLines += "JWT_SECRET_KEY=$JwtSecret"
}

if (-not $resetSecretAdded) {
    $updatedEnvLines += "RESET_SECRET_KEY=$ResetSecret"
}

# Configure secure Redis
Log "Configuring secure Redis settings..."
$redisPasswordAdded = $false
foreach ($line in $envLines) {
    if ($line -match '^REDIS_PASSWORD=(.*)$') {
        $redisPwd = $matches[1]
        if ([string]::IsNullOrEmpty($redisPwd) -or $redisPwd -eq "changeme" -or $redisPwd.Length -lt 16) {
            # Generate strong Redis password
            $redisPwd = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
            $redisPasswordAdded = $true
        }
    }
}

if (-not $redisPasswordAdded) {
    # Add Redis password
    $redisPwd = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
    $updatedEnvLines += "REDIS_PASSWORD=$redisPwd"
    Log "Added Redis password to environment configuration"
}

# Configure secure database password
Log "Configuring secure database settings..."
$dbPasswordUpdated = $false
foreach ($line in $envLines) {
    if ($line -match '^DB_PASSWORD=(.*)$') {
        $dbPwd = $matches[1]
        if ($dbPwd -eq "changeme" -or $dbPwd.Length -lt 12) {
            # Generate strong database password
            $dbPwd = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
            $dbPasswordUpdated = $true
            Log "Generated strong database password"
            
            # Update database user password
            try {
                Log "Updating PostgreSQL user password..."
                $env:PGPASSWORD = $envVars["DB_PASSWORD"]
                $dbUser = $envVars["DB_USER"]
                $dbName = $envVars["DB_NAME"]
                $dbHost = $envVars["DB_HOST"]
                $dbPort = $envVars["DB_PORT"]
                
                $query = "ALTER USER $dbUser WITH PASSWORD '$dbPwd';"
                $psqlPath = "psql"
                
                # Try to find psql executable
                if (-not (Get-Command $psqlPath -ErrorAction SilentlyContinue)) {
                    $psqlPath = "C:\Program Files\PostgreSQL\*\bin\psql.exe"
                    if (-not (Test-Path $psqlPath)) {
                        Log "Warning: Could not find psql executable. Database password will be updated in .env file only."
                        Log "You will need to manually update the PostgreSQL user password."
                    } else {
                        $psqlPath = (Get-Item $psqlPath | Sort-Object -Property FullName -Descending)[0].FullName
                    }
                }
                
                if (Test-Path $psqlPath) {
                    & $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -c $query
                    Log "PostgreSQL user password updated"
                }
            } catch {
                Log "Warning: Failed to update PostgreSQL user password: $_"
                Log "You will need to manually update the PostgreSQL user password."
            }
        }
    }
}

# Configure secure session settings
Log "Configuring secure session settings..."
$sessionExpiryAdded = $false
$refreshTokenExpiryAdded = $false

foreach ($line in $envLines) {
    if ($line -match '^SESSION_EXPIRY=') {
        $updatedEnvLines = $updatedEnvLines -replace '^SESSION_EXPIRY=.*', 'SESSION_EXPIRY=3600'
        $sessionExpiryAdded = $true
    } elseif ($line -match '^REFRESH_TOKEN_EXPIRY=') {
        $updatedEnvLines = $updatedEnvLines -replace '^REFRESH_TOKEN_EXPIRY=.*', 'REFRESH_TOKEN_EXPIRY=86400'
        $refreshTokenExpiryAdded = $true
    }
}

if (-not $sessionExpiryAdded) {
    $updatedEnvLines += "SESSION_EXPIRY=3600"
}

if (-not $refreshTokenExpiryAdded) {
    $updatedEnvLines += "REFRESH_TOKEN_EXPIRY=86400"
}

# Configure rate limiting
Log "Configuring rate limiting..."
$rateLimitAdded = $false
foreach ($line in $envLines) {
    if ($line -match '^RATE_LIMIT_PER_MINUTE=') {
        $updatedEnvLines = $updatedEnvLines -replace '^RATE_LIMIT_PER_MINUTE=.*', 'RATE_LIMIT_PER_MINUTE=60'
        $rateLimitAdded = $true
    }
}

if (-not $rateLimitAdded) {
    $updatedEnvLines += "RATE_LIMIT_PER_MINUTE=60"
}

# Configure secure CORS settings
Log "Configuring secure CORS settings..."
$corsAdded = $false
foreach ($line in $envLines) {
    if ($line -match '^ALLOW_ORIGINS=') {
        $updatedEnvLines = $updatedEnvLines -replace '^ALLOW_ORIGINS=.*', 'ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000'
        $corsAdded = $true
    }
}

if (-not $corsAdded) {
    $updatedEnvLines += "ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000"
}

# Configure secure logging
Log "Configuring secure logging..."
$logLevelAdded = $false
foreach ($line in $envLines) {
    if ($line -match '^LOG_LEVEL=') {
        $updatedEnvLines = $updatedEnvLines -replace '^LOG_LEVEL=.*', 'LOG_LEVEL=INFO'
        $logLevelAdded = $true
    }
}

if (-not $logLevelAdded) {
    $updatedEnvLines += "LOG_LEVEL=INFO"
}

# Save updated .env file
$updatedEnvContent = $updatedEnvLines -join "`n"
Set-Content -Path ".env" -Value $updatedEnvContent

# Create security configuration file
Log "Creating security configuration file..."
$securityConfig = @{
    security = @{
        password_policy = @{
            min_length = 12
            require_uppercase = $true
            require_lowercase = $true
            require_numbers = $true
            require_special_chars = $true
            max_age_days = 90
            prevent_reuse = 5
        }
        session = @{
            expiry_seconds = 3600
            refresh_token_expiry_seconds = 86400
            idle_timeout_seconds = 1800
            max_sessions_per_user = 5
        }
        rate_limiting = @{
            login_attempts_per_minute = 5
            api_requests_per_minute = 60
            api_key_requests_per_minute = 120
        }
        mfa = @{
            required_for_admins = $true
            required_for_api_key_creation = $true
            totp_issuer = "Cryptobot"
        }
        api_keys = @{
            rotation_days = 90
            max_keys_per_user = 5
        }
    }
}

$securityConfigJson = $securityConfig | ConvertTo-Json -Depth 5
Set-Content -Path "config\security\security_config.json" -Value $securityConfigJson

# Set secure file permissions
Log "Setting secure file permissions..."
$acl = Get-Acl ".env"
$acl.SetAccessRuleProtection($true, $false)
$administratorsRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "Allow")
$systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM", "FullControl", "Allow")
$currentUserRule = New-Object System.Security.AccessControl.FileSystemAccessRule([System.Security.Principal.WindowsIdentity]::GetCurrent().Name, "FullControl", "Allow")
$acl.AddAccessRule($administratorsRule)
$acl.AddAccessRule($systemRule)
$acl.AddAccessRule($currentUserRule)
Set-Acl ".env" $acl

$acl = Get-Acl "config\security\security_config.json"
$acl.SetAccessRuleProtection($true, $false)
$acl.AddAccessRule($administratorsRule)
$acl.AddAccessRule($systemRule)
$acl.AddAccessRule($currentUserRule)
Set-Acl "config\security\security_config.json" $acl

Log "Security configuration completed successfully!"
Log "Note: You may need to restart services for some changes to take effect."
exit 0