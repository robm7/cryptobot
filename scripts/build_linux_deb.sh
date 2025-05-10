#!/bin/bash
# Build script for CryptoBot Linux DEB package
#
# This script builds a DEB package for CryptoBot using fpm.
# It first builds the application using PyInstaller, then creates a DEB package.
#
# Usage:
#   ./build_linux_deb.sh [options]
#
# Options:
#   --clean     Clean build and dist directories before building
#   --optimize  Optimize the build for size using UPX
#   --test      Install and run the package after building to verify it works
#
# Example:
#   ./build_linux_deb.sh --clean --optimize

# Exit on error
set -e

# Parse arguments
CLEAN=0
OPTIMIZE=0
TEST=0

for arg in "$@"; do
  case $arg in
    --clean)
      CLEAN=1
      shift
      ;;
    --optimize)
      OPTIMIZE=1
      shift
      ;;
    --test)
      TEST=1
      shift
      ;;
    *)
      # Unknown option
      echo "Unknown option: $arg"
      exit 1
      ;;
  esac
done

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"
PACKAGE_DIR="$DIST_DIR/package"
INSTALL_DIR="/opt/cryptobot"
VENV_DIR="$PROJECT_ROOT/venv"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
DEV_REQUIREMENTS_FILE="$PROJECT_ROOT/requirements-dev.txt"
VERSION="1.0.0"
ARCHITECTURE="amd64"  # or "all" for architecture-independent

# Ensure we're in the project root
cd "$PROJECT_ROOT"

# Output header
echo "===================================================="
echo "CryptoBot Linux DEB Package Build Script"
echo "===================================================="
echo "Project root: $PROJECT_ROOT"
echo "Build directory: $BUILD_DIR"
echo "Distribution directory: $DIST_DIR"
echo "Package directory: $PACKAGE_DIR"
echo "Installation directory: $INSTALL_DIR"
echo "===================================================="

# Clean build and dist directories if requested
if [ $CLEAN -eq 1 ]; then
  echo "Cleaning build and dist directories..."
  if [ -d "$BUILD_DIR" ]; then
    rm -rf "$BUILD_DIR"
  fi
  if [ -d "$DIST_DIR" ]; then
    rm -rf "$DIST_DIR"
  fi
  echo "Cleaned build and dist directories."
fi

# Create package directory if it doesn't exist
if [ ! -d "$PACKAGE_DIR" ]; then
  mkdir -p "$PACKAGE_DIR"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
  echo "Virtual environment created."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "Virtual environment activated."

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r "$REQUIREMENTS_FILE"
pip install -r "$DEV_REQUIREMENTS_FILE"
pip install pyinstaller

if [ $OPTIMIZE -eq 1 ]; then
  # Install UPX for compression
  echo "Installing UPX for executable compression..."
  
  # Check if UPX is already installed
  if command -v upx &> /dev/null; then
    echo "UPX is already installed."
    UPX_PATH=$(command -v upx)
  else
    # Try to install UPX using package manager
    if command -v apt-get &> /dev/null; then
      echo "Installing UPX using apt..."
      sudo apt-get update
      sudo apt-get install -y upx
      UPX_PATH=$(command -v upx)
    elif command -v dnf &> /dev/null; then
      echo "Installing UPX using dnf..."
      sudo dnf install -y upx
      UPX_PATH=$(command -v upx)
    elif command -v yum &> /dev/null; then
      echo "Installing UPX using yum..."
      sudo yum install -y upx
      UPX_PATH=$(command -v upx)
    elif command -v pacman &> /dev/null; then
      echo "Installing UPX using pacman..."
      sudo pacman -S --noconfirm upx
      UPX_PATH=$(command -v upx)
    else
      echo "Could not install UPX automatically. Please install it manually."
      OPTIMIZE=0
    fi
  fi
  
  if [ $OPTIMIZE -eq 1 ]; then
    echo "UPX installed at: $UPX_PATH"
  fi
fi

# Install fpm for package creation
echo "Installing fpm for package creation..."
if ! command -v fpm &> /dev/null; then
  # Check if Ruby is installed
  if ! command -v ruby &> /dev/null; then
    echo "Ruby not found. Installing..."
    if command -v apt-get &> /dev/null; then
      sudo apt-get update
      sudo apt-get install -y ruby ruby-dev build-essential
    elif command -v dnf &> /dev/null; then
      sudo dnf install -y ruby ruby-devel gcc make rpm-build
    elif command -v yum &> /dev/null; then
      sudo yum install -y ruby ruby-devel gcc make rpm-build
    elif command -v pacman &> /dev/null; then
      sudo pacman -S --noconfirm ruby base-devel
    else
      echo "Could not install Ruby automatically. Please install it manually."
      exit 1
    fi
  fi
  
  # Install fpm
  sudo gem install --no-document fpm
fi
echo "fpm installed."

echo "Dependencies installed."

# Run PyInstaller for the main application
echo "Building main application with PyInstaller..."
if [ $OPTIMIZE -eq 1 ]; then
  pyinstaller --clean "$PROJECT_ROOT/pyinstaller_config.spec" --upx-dir="$(dirname "$UPX_PATH")"
else
  pyinstaller --clean "$PROJECT_ROOT/pyinstaller_config.spec"
fi
echo "PyInstaller build completed."

# Create a PyInstaller spec file for the Quick Start Launcher
echo "Creating PyInstaller spec file for the Quick Start Launcher..."
cat > "$PROJECT_ROOT/launcher_linux.spec" << EOF
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['quick_start_launcher.py'],
    pathex=['$PROJECT_ROOT'],
    binaries=[],
    datas=[
        ('static', 'static'),
    ],
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
    name='cryptobot-launcher',
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
    name='cryptobot-launcher',
)
EOF
# Run PyInstaller for the Quick Start Launcher
echo "Building Quick Start Launcher with PyInstaller..."
if [ $OPTIMIZE -eq 1 ]; then
  pyinstaller --clean "$PROJECT_ROOT/launcher_linux.spec" --upx-dir="$(dirname "$UPX_PATH")"
else
  pyinstaller --clean "$PROJECT_ROOT/launcher_linux.spec"
fi
echo "PyInstaller build completed for Quick Start Launcher."

# Verify the build
if [ -d "$DIST_DIR/cryptobot" ] && [ -f "$DIST_DIR/cryptobot/cryptobot" ]; then
  echo "Directory-based executable built successfully."
else
  echo "Directory-based executable build failed!"
  exit 1
fi

if [ -d "$DIST_DIR/cryptobot-launcher" ] && [ -f "$DIST_DIR/cryptobot-launcher/cryptobot-launcher" ]; then
  echo "Quick Start Launcher built successfully."
else
  echo "Quick Start Launcher build failed!"
  exit 1
fi

# Prepare package structure
echo "Preparing package structure..."
mkdir -p "$PACKAGE_DIR$INSTALL_DIR"
mkdir -p "$PACKAGE_DIR/usr/bin"
mkdir -p "$PACKAGE_DIR/usr/share/applications"
mkdir -p "$PACKAGE_DIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$PACKAGE_DIR/etc/cryptobot"
mkdir -p "$PACKAGE_DIR/lib/systemd/system"

# Copy application files
echo "Copying application files..."
cp -R "$DIST_DIR/cryptobot/"* "$PACKAGE_DIR$INSTALL_DIR/"
cp -R "$DIST_DIR/cryptobot-launcher/"* "$PACKAGE_DIR$INSTALL_DIR/"
chmod +x "$PACKAGE_DIR$INSTALL_DIR/cryptobot"
chmod +x "$PACKAGE_DIR$INSTALL_DIR/cryptobot-launcher"

# Create symlinks in /usr/bin
echo "Creating symlinks..."
cat > "$PACKAGE_DIR/usr/bin/cryptobot" << EOF
#!/bin/bash
$INSTALL_DIR/cryptobot "\$@"
EOF
chmod +x "$PACKAGE_DIR/usr/bin/cryptobot"

cat > "$PACKAGE_DIR/usr/bin/cryptobot-launcher" << EOF
#!/bin/bash
$INSTALL_DIR/cryptobot-launcher "\$@"
EOF
chmod +x "$PACKAGE_DIR/usr/bin/cryptobot-launcher"

# Create desktop entries
echo "Creating desktop entries..."
cat > "$PACKAGE_DIR/usr/share/applications/cryptobot.desktop" << EOF
[Desktop Entry]
Name=CryptoBot
Comment=Automated Cryptocurrency Trading System
Exec=$INSTALL_DIR/cryptobot
Icon=cryptobot
Terminal=false
Type=Application
Categories=Finance;
EOF

cat > "$PACKAGE_DIR/usr/share/applications/cryptobot-launcher.desktop" << EOF
[Desktop Entry]
Name=CryptoBot Launcher
Comment=CryptoBot Quick Start Launcher
Exec=$INSTALL_DIR/cryptobot-launcher
Icon=cryptobot
Terminal=false
Type=Application
Categories=Finance;
EOF

# Copy icon
echo "Copying icon..."
if [ -f "$PROJECT_ROOT/static/favicon.png" ]; then
  cp "$PROJECT_ROOT/static/favicon.png" "$PACKAGE_DIR/usr/share/icons/hicolor/256x256/apps/cryptobot.png"
elif [ -f "$PROJECT_ROOT/static/favicon.ico" ]; then
  # Convert ICO to PNG if needed
  if command -v convert &> /dev/null; then
    convert "$PROJECT_ROOT/static/favicon.ico" "$PACKAGE_DIR/usr/share/icons/hicolor/256x256/apps/cryptobot.png"
  else
    echo "ImageMagick not found. Installing..."
    if command -v apt-get &> /dev/null; then
      sudo apt-get update
      sudo apt-get install -y imagemagick
    elif command -v dnf &> /dev/null; then
      sudo dnf install -y imagemagick
    elif command -v yum &> /dev/null; then
      sudo yum install -y imagemagick
    elif command -v pacman &> /dev/null; then
      sudo pacman -S --noconfirm imagemagick
    else
      echo "Could not install ImageMagick automatically. Using default icon."
    fi
    convert "$PROJECT_ROOT/static/favicon.ico" "$PACKAGE_DIR/usr/share/icons/hicolor/256x256/apps/cryptobot.png"
  fi
# Create systemd service file
echo "Creating systemd service file..."
cat > "$PACKAGE_DIR/lib/systemd/system/cryptobot.service" << EOF
[Unit]
Description=CryptoBot Trading System
After=network.target

[Service]
Type=simple
User=root
ExecStart=$INSTALL_DIR/cryptobot
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=cryptobot

[Install]
WantedBy=multi-user.target
EOF

# Copy configuration files
echo "Copying configuration files..."
cp "$PROJECT_ROOT/config/default_config.json" "$PACKAGE_DIR/etc/cryptobot/config.json"

# Create post-installation script
echo "Creating post-installation script..."
mkdir -p "$PACKAGE_DIR/DEBIAN"
cat > "$PACKAGE_DIR/DEBIAN/postinst" << EOF
#!/bin/bash
# Post-installation script for CryptoBot

# Update icon cache
if command -v update-icon-caches &> /dev/null; then
  update-icon-caches /usr/share/icons/hicolor
fi

# Enable systemd service but don't start it
if command -v systemctl &> /dev/null; then
  systemctl daemon-reload
  systemctl enable cryptobot.service
fi

# Create data directory
mkdir -p /var/lib/cryptobot/data
chmod 755 /var/lib/cryptobot/data

# Set permissions
chmod 755 $INSTALL_DIR/cryptobot
chmod 755 $INSTALL_DIR/cryptobot-launcher

echo "CryptoBot has been installed successfully."
echo "You can start it by running 'cryptobot' or 'cryptobot-launcher'."
echo "Or you can start the service with 'systemctl start cryptobot'."
EOF
chmod +x "$PACKAGE_DIR/DEBIAN/postinst"

# Create pre-removal script
echo "Creating pre-removal script..."
cat > "$PACKAGE_DIR/DEBIAN/prerm" << EOF
#!/bin/bash
# Pre-removal script for CryptoBot

# Stop and disable systemd service
if command -v systemctl &> /dev/null; then
  systemctl stop cryptobot.service
  systemctl disable cryptobot.service
fi

echo "CryptoBot is being removed."
EOF
chmod +x "$PACKAGE_DIR/DEBIAN/prerm"

# Create control file
echo "Creating control file..."
cat > "$PACKAGE_DIR/DEBIAN/control" << EOF
Package: cryptobot
Version: $VERSION
Section: finance
Priority: optional
Architecture: $ARCHITECTURE
Depends: python3 (>= 3.7), python3-tk, libssl-dev
Maintainer: CryptoBot Team <support@cryptobot.example.com>
Description: Automated Cryptocurrency Trading System
 CryptoBot is an automated trading system for cryptocurrency markets
 that implements various trading strategies with risk management
 and portfolio optimization.
 .
 Features:
  * Multi-exchange support
  * Strategy engine
  * Risk management
  * Backtesting
  * Paper trading
  * Real-time monitoring
EOF

# Build the DEB package
echo "Building DEB package..."
DEB_FILE="$DIST_DIR/cryptobot_${VERSION}_${ARCHITECTURE}.deb"
fpm -s dir -t deb -n cryptobot -v $VERSION -C "$PACKAGE_DIR" \
    --description "Automated Cryptocurrency Trading System" \
    --url "https://cryptobot.example.com" \
    --license "MIT" \
    --vendor "CryptoBot Team" \
    --maintainer "support@cryptobot.example.com" \
    --after-install "$PACKAGE_DIR/DEBIAN/postinst" \
    --before-remove "$PACKAGE_DIR/DEBIAN/prerm" \
    --deb-priority optional \
    --category finance \
    --deb-no-default-config-files \
    --deb-systemd "$PACKAGE_DIR/lib/systemd/system/cryptobot.service" \
    --architecture $ARCHITECTURE \
    --depends "python3 >= 3.7" \
    --depends "python3-tk" \
    --depends "libssl-dev" \
    --package "$DEB_FILE"

echo "DEB package built: $DEB_FILE"

# Test the package if requested
if [ $TEST -eq 1 ]; then
  echo "Testing DEB package..."
  sudo dpkg -i "$DEB_FILE"
  echo "Package installed. Testing..."
  cryptobot --version
  echo "Package test completed."
  
  # Ask if the user wants to remove the package
  read -p "Do you want to remove the package now? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo apt-get remove -y cryptobot
    echo "Package removed."
  fi
fi

# Deactivate virtual environment
deactivate
echo "Virtual environment deactivated."

# Output summary
echo "===================================================="
echo "Build Summary"
echo "===================================================="
echo "DEB package: $DEB_FILE"
echo "===================================================="
echo "Build completed successfully!"
fi