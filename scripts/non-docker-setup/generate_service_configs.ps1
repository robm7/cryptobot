# Cryptobot Service Configuration Generator for Windows
# This script generates service-specific configuration files from templates

# Function to display messages
function Log {
    param (
        [string]$Message
    )
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
}

# Function to generate a configuration file from a template and environment variables
function Generate-Config {
    param (
        [string]$TemplatePath,
        [string]$OutputPath,
        [hashtable]$Variables
    )
    
    if (-not (Test-Path $TemplatePath)) {
        Log "Error: Template file not found at $TemplatePath"
        return $false
    }
    
    Log "Generating configuration file from $TemplatePath to $OutputPath"
    
    # Read the template content
    $content = Get-Content -Path $TemplatePath -Raw
    
    # Replace variables in the template
    foreach ($key in $Variables.Keys) {
        $placeholder = "{{$key}}"
        $content = $content -replace [regex]::Escape($placeholder), $Variables[$key]
    }
    
    # Create the directory if it doesn't exist
    $outputDir = Split-Path -Path $OutputPath -Parent
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    # Write the content to the output file
    Set-Content -Path $OutputPath -Value $content -Force
    
    Log "Configuration file generated at $OutputPath"
    return $true
}

# Function to load environment variables from .env file
function Load-EnvFile {
    param (
        [string]$FilePath
    )
    
    $variables = @{}
    
    if (Test-Path $FilePath) {
        $content = Get-Content -Path $FilePath
        
        foreach ($line in $content) {
            if ($line -match '^\s*([^#][^=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                $variables[$key] = $value
            }
        }
    }
    
    return $variables
}

# Display welcome message
Log "Generating service-specific configuration files..."

# Get project root directory
$projectRoot = $PSScriptRoot | Split-Path | Split-Path

# Define services
$services = @("auth", "strategy", "trade", "backtest", "data")

# Process each service
foreach ($service in $services) {
    Log "Processing $service service..."
    
    # Define paths
    $templatePath = "$projectRoot\config\non-docker\$service\config.yaml"
    $envFilePath = "$projectRoot\$service\.env"
    $outputPath = "$projectRoot\$service\config.yaml"
    
    # Load environment variables
    $envVars = Load-EnvFile -FilePath $envFilePath
    
    # Generate configuration file
    $success = Generate-Config -TemplatePath $templatePath -OutputPath $outputPath -Variables $envVars
    
    if ($success) {
        Log "$service service configuration generated successfully."
    } else {
        Log "Failed to generate $service service configuration."
    }
}

Log "Service configuration generation completed!"
exit 0