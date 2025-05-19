#Requires -Version 5.1

# Script to generate OpenAPI specifications from running FastAPI services using PowerShell.

# --- Configuration ---
# Adjust these service names and ports according to your project's setup.
# The service name here is used for the output filename and informational messages.
# The hostname is assumed to be localhost.

$services = @(
    @{ Name = "auth"; Port = 8000 },
    @{ Name = "auth-service"; Port = 5000 }, # Updated port, Flask app
    @{ Name = "backtest"; Port = 8002 },   # Assuming this is the intended operational port
    @{ Name = "data"; Port = 8001 },     # Updated port
    @{ Name = "strategy"; Port = 8004 },   # Assuming this is the intended operational port
    @{ Name = "trade"; Port = 8005 }     # Assuming this is the intended operational port (main.py defaults to 8000)
)

$outputDir = "docs/api"
$baseUrlPrefix = "http://localhost"

# --- Script Logic ---

Write-Host "Starting OpenAPI specification generation..."

# Create the output directory if it doesn't exist
if (-not (Test-Path -Path $outputDir -PathType Container)) {
    try {
        New-Item -ItemType Directory -Path $outputDir -ErrorAction Stop | Out-Null
        Write-Host "Output directory: '$outputDir' created."
    }
    catch {
        Write-Error "Could not create output directory '$outputDir'. Please check permissions."
        Write-Error $_.Exception.Message
        exit 1
    }
} else {
    Write-Host "Output directory: '$outputDir'"
}

# Loop through services and fetch their openapi.json
foreach ($service in $services) {
    $serviceName = $service.Name
    $servicePort = $service.Port
    
    $serviceUrl = "$baseUrlPrefix`:$servicePort/openapi.json" # Backtick for colon in string
    $outputFile = Join-Path -Path $outputDir -ChildPath "$serviceName-openapi.json"
    
    Write-Host ""
    Write-Host "Fetching OpenAPI spec for '$serviceName' from $serviceUrl..."
    
    try {
        # Use Invoke-WebRequest to fetch the openapi.json
        Invoke-WebRequest -Uri $serviceUrl -OutFile $outputFile -ErrorAction Stop -TimeoutSec 10 # Added timeout
        
        if (Test-Path -Path $outputFile) {
            Write-Host "Successfully saved OpenAPI spec to '$outputFile'"
        } else {
            # This case should ideally be caught by ErrorAction Stop, but as a fallback
            Write-Warning "OpenAPI spec for '$serviceName' might not have been saved correctly, even though no explicit error was thrown."
        }
    }
    catch {
        Write-Error "Failed to fetch OpenAPI spec for '$serviceName'."
        Write-Error "Please ensure the '$serviceName' service is running on port '$servicePort' and accessible at '$serviceUrl'."
        Write-Error "Error details: $($_.Exception.Message)"
        # Consider whether to exit on first error or continue with other services
        # For now, it continues.
    }
}

Write-Host ""
Write-Host "OpenAPI specification generation process completed."
Write-Host "Please check the '$outputDir' directory for the generated files."
Write-Host "If any errors occurred, ensure the respective services are running and accessible."