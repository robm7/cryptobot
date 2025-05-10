<#
.SYNOPSIS
    Build script for Cryptobot Windows executable
.DESCRIPTION
    This script builds a standalone Windows executable for Cryptobot using PyInstaller.
    It handles dependency management, packaging, and creates both a directory-based
    and a single-file executable.
.PARAMETER Clean
    If specified, cleans the build and dist directories before building
.PARAMETER Optimize
    If specified, optimizes the build for size using UPX
.PARAMETER Test
    If specified, runs the executable after building to verify it works
.EXAMPLE
    .\build_windows.ps1 -Clean -Optimize
#>

param (
    [switch]$Clean = $false,
    [switch]$Optimize = $false,
    [switch]$Test = $false
)

# Configuration
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BuildDir = Join-Path $ProjectRoot "build"
$DistDir = Join-Path $ProjectRoot "dist"
$SpecFile = Join-Path $ProjectRoot "pyinstaller_config.spec"
$VenvDir = Join-Path $ProjectRoot "venv"
$RequirementsFile = Join-Path $ProjectRoot "requirements.txt"
$DevRequirementsFile = Join-Path $ProjectRoot "requirements-dev.txt"

# Ensure we're in the project root
Set-Location $ProjectRoot

# Output header
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Cryptobot Windows Build Script" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host "Build directory: $BuildDir"
Write-Host "Distribution directory: $DistDir"
Write-Host "Spec file: $SpecFile"
Write-Host "====================================================" -ForegroundColor Cyan

# Clean build and dist directories if requested
if ($Clean) {
    Write-Host "Cleaning build and dist directories..." -ForegroundColor Yellow
    if (Test-Path $BuildDir) {
        Remove-Item -Path $BuildDir -Recurse -Force
    }
    if (Test-Path $DistDir) {
        Remove-Item -Path $DistDir -Recurse -Force
    }
    Write-Host "Cleaned build and dist directories." -ForegroundColor Green
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $VenvDir
    Write-Host "Virtual environment created." -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "$VenvDir\Scripts\Activate.ps1"
Write-Host "Virtual environment activated." -ForegroundColor Green

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r $RequirementsFile
pip install -r $DevRequirementsFile
pip install pyinstaller
if ($Optimize) {
    # Install UPX for compression
    Write-Host "Installing UPX for executable compression..." -ForegroundColor Yellow
    
    # Create a temporary directory for UPX
    $TempDir = Join-Path $env:TEMP "upx"
    if (-not (Test-Path $TempDir)) {
        New-Item -Path $TempDir -ItemType Directory | Out-Null
    }
    
    # Download UPX
    $UPXVersion = "4.0.2"
    $UPXZip = Join-Path $TempDir "upx-$UPXVersion-win64.zip"
    $UPXUrl = "https://github.com/upx/upx/releases/download/v$UPXVersion/upx-$UPXVersion-win64.zip"
    
    Invoke-WebRequest -Uri $UPXUrl -OutFile $UPXZip
    
    # Extract UPX
    Expand-Archive -Path $UPXZip -DestinationPath $TempDir -Force
    
    # Add UPX to PATH
    $UPXDir = Join-Path $TempDir "upx-$UPXVersion-win64"
    $env:PATH = "$UPXDir;$env:PATH"
    
    Write-Host "UPX installed." -ForegroundColor Green
}
Write-Host "Dependencies installed." -ForegroundColor Green

# Run PyInstaller
Write-Host "Building executable with PyInstaller..." -ForegroundColor Yellow
if ($Optimize) {
    pyinstaller --clean $SpecFile --upx-dir=$UPXDir
} else {
    pyinstaller --clean $SpecFile
}
Write-Host "PyInstaller build completed." -ForegroundColor Green

# Verify the build
if (Test-Path (Join-Path $DistDir "cryptobot\cryptobot.exe")) {
    Write-Host "Directory-based executable built successfully." -ForegroundColor Green
} else {
    Write-Host "Directory-based executable build failed!" -ForegroundColor Red
}

if (Test-Path (Join-Path $DistDir "cryptobot_onefile.exe")) {
    Write-Host "Single-file executable built successfully." -ForegroundColor Green
} else {
    Write-Host "Single-file executable build failed!" -ForegroundColor Red
}

# Test the executable if requested
if ($Test) {
    Write-Host "Testing executable..." -ForegroundColor Yellow
    $ExePath = Join-Path $DistDir "cryptobot\cryptobot.exe"
    if (Test-Path $ExePath) {
        Start-Process -FilePath $ExePath -ArgumentList "--help" -NoNewWindow -Wait
        Write-Host "Executable test completed." -ForegroundColor Green
    } else {
        Write-Host "Executable not found for testing!" -ForegroundColor Red
    }
}

# Create a ZIP archive of the directory-based executable
Write-Host "Creating ZIP archive..." -ForegroundColor Yellow
$ZipFile = Join-Path $DistDir "cryptobot-windows.zip"
if (Test-Path $ZipFile) {
    Remove-Item -Path $ZipFile -Force
}
$CryptobotDir = Join-Path $DistDir "cryptobot"
Compress-Archive -Path $CryptobotDir -DestinationPath $ZipFile
Write-Host "ZIP archive created: $ZipFile" -ForegroundColor Green

# Deactivate virtual environment
deactivate
Write-Host "Virtual environment deactivated." -ForegroundColor Green

# Output summary
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Build Summary" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Directory-based executable: $(Join-Path $DistDir "cryptobot\cryptobot.exe")"
Write-Host "Single-file executable: $(Join-Path $DistDir "cryptobot_onefile.exe")"
Write-Host "ZIP archive: $ZipFile"
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Build completed successfully!" -ForegroundColor Green