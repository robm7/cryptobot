# Cryptobot Environment Activation Script
# Run this script to activate the Python virtual environment

Write-Host "Activating Cryptobot Python virtual environment..."
.\venv\Scripts\Activate.ps1

# Set environment variables
if (Test-Path .env) {
    Write-Host "Loading environment variables from .env file..."
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^#][^=]*)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Variable -Name $key -Value $value -Scope Global
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
}

Write-Host "Cryptobot environment activated!"
Write-Host "Run 'deactivate' to exit the virtual environment."
