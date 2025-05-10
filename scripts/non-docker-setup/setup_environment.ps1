# Cryptobot Master Environment Setup Script for Windows
# This script orchestrates the entire environment setup process

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
Log "Welcome to the Cryptobot Environment Setup!"
Log "This script will set up the complete environment for the Cryptobot application."
Log "The setup process includes:"
Log "1. Base system preparation"
Log "2. PostgreSQL database installation and configuration"
Log "3. Redis installation and configuration"
Log "4. Python environment setup"
Log ""
Log "The setup process may take several minutes to complete."
Log ""

Write-Host "Press Enter to continue or Ctrl+C to cancel..." -NoNewline
$null = Read-Host

# Create a directory for logs
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# Step 1: Base system preparation
Log "Step 1: Base system preparation"
Log "Running setup_base_system.ps1..."
$baseSystemOutput = & "$PSScriptRoot\setup_base_system.ps1" 2>&1
$baseSystemOutput | Out-File -FilePath "logs\setup_base_system.log"
$baseSystemOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Base system setup failed. Please check logs\setup_base_system.log for details."
    exit 1
}

Log "Base system setup completed successfully!"

# Step 2: PostgreSQL database installation and configuration
Log "Step 2: PostgreSQL database installation and configuration"
Log "Running setup_database.ps1..."
$databaseOutput = & "$PSScriptRoot\setup_database.ps1" 2>&1
$databaseOutput | Out-File -FilePath "logs\setup_database.log"
$databaseOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Database setup failed. Please check logs\setup_database.log for details."
    exit 1
}

Log "Database setup completed successfully!"

# Step 3: Redis installation and configuration
Log "Step 3: Redis installation and configuration"
Log "Running setup_redis.ps1..."
$redisOutput = & "$PSScriptRoot\setup_redis.ps1" 2>&1
$redisOutput | Out-File -FilePath "logs\setup_redis.log"
$redisOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Redis setup failed. Please check logs\setup_redis.log for details."
    exit 1
}

Log "Redis setup completed successfully!"

# Step 4: Python environment setup
Log "Step 4: Python environment setup"
Log "Running setup_python_env.ps1..."
$pythonEnvOutput = & "$PSScriptRoot\setup_python_env.ps1" 2>&1
$pythonEnvOutput | Out-File -FilePath "logs\setup_python_env.log"
$pythonEnvOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Python environment setup failed. Please check logs\setup_python_env.log for details."
    exit 1
}

Log "Python environment setup completed successfully!"

# Final steps and verification
Log "Verifying installation..."

# Check if PostgreSQL is running
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if ($pgService -and $pgService.Status -eq "Running") {
    Log "PostgreSQL is running correctly."
} else {
    Log "Warning: PostgreSQL may not be running correctly."
}

# Check if Redis is running
$redisService = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
if ($redisService -and $redisService.Status -eq "Running") {
    Log "Redis is running correctly."
} else {
    Log "Warning: Redis may not be running correctly."
}

# Check if Python virtual environment was created
if (Test-Path "venv") {
    Log "Python virtual environment is set up correctly."
} else {
    Log "Warning: Python virtual environment may not be set up correctly."
}

Log "Environment setup completed successfully!"
Log ""
Log "To activate the Python virtual environment, run:"
Log "  .\activate_env.ps1"
Log ""
Log "To start the Cryptobot application, run:"
Log "  .\run_cryptobot.ps1"
Log ""
Log "Thank you for installing Cryptobot!"

exit 0