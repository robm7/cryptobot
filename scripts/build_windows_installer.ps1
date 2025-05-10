<#
.SYNOPSIS
    Build script for CryptoBot Windows installer
.DESCRIPTION
    This script builds a Windows installer for CryptoBot using Inno Setup.
    It first builds the application using PyInstaller, then creates an installer
    using the Inno Setup script.
.PARAMETER Clean
    If specified, cleans the build and dist directories before building
.PARAMETER Optimize
    If specified, optimizes the build for size using UPX
.PARAMETER Test
    If specified, runs the installer after building to verify it works
.EXAMPLE
    .\build_windows_installer.ps1 -Clean -Optimize
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
$InstallerDir = Join-Path $DistDir "installer"
$SpecFile = Join-Path $ProjectRoot "pyinstaller_config.spec"
$InnoSetupScript = Join-Path $ProjectRoot "scripts\windows_installer.iss"
$VenvDir = Join-Path $ProjectRoot "venv"
$RequirementsFile = Join-Path $ProjectRoot "requirements.txt"
$DevRequirementsFile = Join-Path $ProjectRoot "requirements-dev.txt"

# Ensure we're in the project root
Set-Location $ProjectRoot

# Output header
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "CryptoBot Windows Installer Build Script" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host "Build directory: $BuildDir"
Write-Host "Distribution directory: $DistDir"
Write-Host "Installer directory: $InstallerDir"
Write-Host "Spec file: $SpecFile"
Write-Host "Inno Setup script: $InnoSetupScript"
Write-Host "====================================================" -ForegroundColor Cyan

# Check if Inno Setup is installed
$InnoSetupPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $InnoSetupPath)) {
    $InnoSetupPath = "C:\Program Files\Inno Setup 6\ISCC.exe"
    if (-not (Test-Path $InnoSetupPath)) {
        Write-Host "Inno Setup not found. Downloading and installing..." -ForegroundColor Yellow
        
        # Download Inno Setup
        $InnoSetupInstallerUrl = "https://jrsoftware.org/download.php/is.exe"
        $InnoSetupInstallerPath = Join-Path $env:TEMP "innosetup-installer.exe"
        
        Invoke-WebRequest -Uri $InnoSetupInstallerUrl -OutFile $InnoSetupInstallerPath
        
        # Install Inno Setup
        Start-Process -FilePath $InnoSetupInstallerPath -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-" -Wait
        
        # Check if installation was successful
        $InnoSetupPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        if (-not (Test-Path $InnoSetupPath)) {
            $InnoSetupPath = "C:\Program Files\Inno Setup 6\ISCC.exe"
            if (-not (Test-Path $InnoSetupPath)) {
                Write-Host "Failed to install Inno Setup. Please install it manually." -ForegroundColor Red
                exit 1
            }
        }
        
        Write-Host "Inno Setup installed successfully." -ForegroundColor Green
    }
}

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

# Create installer directory if it doesn't exist
if (-not (Test-Path $InstallerDir)) {
    New-Item -Path $InstallerDir -ItemType Directory | Out-Null
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

# Build the Quick Start Launcher
Write-Host "Building Quick Start Launcher..." -ForegroundColor Yellow
$LauncherSpecFile = @"
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['quick_start_launcher.py'],
    pathex=['$ProjectRoot'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='quick_start_launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon.ico'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='quick_start_launcher',
)
"@

$LauncherSpecPath = Join-Path $ProjectRoot "quick_start_launcher.spec"
Set-Content -Path $LauncherSpecPath -Value $LauncherSpecFile

if ($Optimize) {
    pyinstaller --clean $LauncherSpecPath --upx-dir=$UPXDir
} else {
    pyinstaller --clean $LauncherSpecPath
}

# Run PyInstaller for the main application
Write-Host "Building main application with PyInstaller..." -ForegroundColor Yellow
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
    exit 1
}

if (Test-Path (Join-Path $DistDir "cryptobot_onefile.exe")) {
    Write-Host "Single-file executable built successfully." -ForegroundColor Green
} else {
    Write-Host "Single-file executable build failed!" -ForegroundColor Red
}

# Copy the Quick Start Launcher to the main application directory
Write-Host "Copying Quick Start Launcher to main application directory..." -ForegroundColor Yellow
$LauncherExe = Join-Path $DistDir "quick_start_launcher\quick_start_launcher.exe"
$DestDir = Join-Path $DistDir "cryptobot"
if (Test-Path $LauncherExe) {
    Copy-Item -Path $LauncherExe -Destination $DestDir
    Write-Host "Quick Start Launcher copied successfully." -ForegroundColor Green
} else {
    Write-Host "Quick Start Launcher not found!" -ForegroundColor Red
}

# Create post-installation script
Write-Host "Creating post-installation script..." -ForegroundColor Yellow
$PostInstallScript = @"
@echo off
echo Running post-installation tasks...

REM Create necessary directories
if not exist "%APPDATA%\CryptoBot\data" mkdir "%APPDATA%\CryptoBot\data"
if not exist "%APPDATA%\CryptoBot\logs" mkdir "%APPDATA%\CryptoBot\logs"

REM Copy default configuration if it doesn't exist
if not exist "%APPDATA%\CryptoBot\config.json" copy "%~dp0..\config\default_config.json" "%APPDATA%\CryptoBot\config.json"

echo Post-installation tasks completed.
"@

$ScriptsDir = Join-Path $DistDir "cryptobot\scripts"
if (-not (Test-Path $ScriptsDir)) {
    New-Item -Path $ScriptsDir -ItemType Directory | Out-Null
}
$PostInstallScriptPath = Join-Path $ScriptsDir "post_install.bat"
Set-Content -Path $PostInstallScriptPath -Value $PostInstallScript

# Build the installer with Inno Setup
Write-Host "Building installer with Inno Setup..." -ForegroundColor Yellow
& $InnoSetupPath $InnoSetupScript
Write-Host "Installer build completed." -ForegroundColor Green

# Verify the installer
$InstallerPath = Join-Path $InstallerDir "cryptobot-setup.exe"
if (Test-Path $InstallerPath) {
    Write-Host "Installer built successfully: $InstallerPath" -ForegroundColor Green
} else {
    Write-Host "Installer build failed!" -ForegroundColor Red
    exit 1
}

# Test the installer if requested
if ($Test) {
    Write-Host "Testing installer..." -ForegroundColor Yellow
    Start-Process -FilePath $InstallerPath -ArgumentList "/SILENT /SUPPRESSMSGBOXES /NORESTART /SP-" -Wait
    Write-Host "Installer test completed." -ForegroundColor Green
}

# Deactivate virtual environment
deactivate
Write-Host "Virtual environment deactivated." -ForegroundColor Green

# Output summary
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Build Summary" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Directory-based executable: $(Join-Path $DistDir "cryptobot\cryptobot.exe")"
Write-Host "Single-file executable: $(Join-Path $DistDir "cryptobot_onefile.exe")"
Write-Host "Installer: $InstallerPath"
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Build completed successfully!" -ForegroundColor Green