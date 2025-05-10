# Cryptobot Configuration Migration Script for Windows
# This script orchestrates the entire configuration migration process

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
    Log "Warning: Some operations may require administrator privileges."
}

# Display welcome message
Log "Welcome to the Cryptobot Configuration Migration!"
Log "This script will migrate Docker configurations to non-Docker configurations."
Log "The migration process includes:"
Log "1. Creating template configuration files"
Log "2. Setting up environment variables"
Log "3. Generating service-specific configurations"
Log ""
Log "The migration process may take several minutes to complete."
Log ""

Write-Host "Press Enter to continue or Ctrl+C to cancel..." -NoNewline
$null = Read-Host

# Get project root directory
$projectRoot = $PSScriptRoot | Split-Path | Split-Path

# Create a directory for logs
New-Item -ItemType Directory -Force -Path "$projectRoot\logs" | Out-Null

# Step 1: Run the configuration migration utility
Log "Step 1: Running configuration migration utility..."
Log "Running migrate_config.py..."

$pythonPath = "python"
$migrateConfigPath = "$PSScriptRoot\migrate_config.py"

$migrateOutput = & $pythonPath $migrateConfigPath --project-root $projectRoot 2>&1
$migrateOutput | Out-File -FilePath "$projectRoot\logs\migrate_config.log"
$migrateOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Configuration migration failed. Please check logs\migrate_config.log for details."
    exit 1
}

Log "Configuration migration completed successfully!"

# Step 2: Set up environment variables
Log "Step 2: Setting up environment variables..."
Log "Running setup_env_vars.ps1..."

$envVarsOutput = & "$PSScriptRoot\setup_env_vars.ps1" 2>&1
$envVarsOutput | Out-File -FilePath "$projectRoot\logs\setup_env_vars.log"
$envVarsOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Environment variables setup failed. Please check logs\setup_env_vars.log for details."
    exit 1
}

Log "Environment variables setup completed successfully!"

# Step 3: Generate service-specific configurations
Log "Step 3: Generating service-specific configurations..."
Log "Running generate_service_configs.ps1..."

$serviceConfigsOutput = & "$PSScriptRoot\generate_service_configs.ps1" 2>&1
$serviceConfigsOutput | Out-File -FilePath "$projectRoot\logs\generate_service_configs.log"
$serviceConfigsOutput | Write-Host

if ($LASTEXITCODE -ne 0) {
    Log "Error: Service configuration generation failed. Please check logs\generate_service_configs.log for details."
    exit 1
}

Log "Service configuration generation completed successfully!"

# Final steps and verification
Log "Verifying configuration files..."

# Check if configuration files were created
$services = @("auth", "strategy", "trade", "backtest", "data")
$allConfigsCreated = $true

foreach ($service in $services) {
    $configPath = "$projectRoot\$service\config.yaml"
    $envPath = "$projectRoot\$service\.env"
    
    if (-not (Test-Path $configPath)) {
        Log "Warning: Configuration file not found for $service service: $configPath"
        $allConfigsCreated = $false
    }
    
    if (-not (Test-Path $envPath)) {
        Log "Warning: Environment file not found for $service service: $envPath"
        $allConfigsCreated = $false
    }
}

if ($allConfigsCreated) {
    Log "All configuration files were created successfully."
} else {
    Log "Warning: Some configuration files may be missing."
}

Log "Configuration migration completed successfully!"
Log ""
Log "The following files have been created:"
Log "1. Template configuration files in config/non-docker/"
Log "2. Environment variable files (.env) in each service directory"
Log "3. Service-specific configuration files (config.yaml) in each service directory"
Log ""
Log "To start the services with the new configuration:"
Log "1. Activate the Python virtual environment"
Log "2. Run each service with the new configuration"
Log ""
Log "Thank you for using the Cryptobot Configuration Migration Utility!"

exit 0