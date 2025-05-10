#!/bin/bash
# Build script for CryptoBot macOS application bundle
#
# This script builds a macOS application bundle (.app) for CryptoBot using PyInstaller.
# It handles dependency management, packaging, and creates a proper macOS application bundle.
#
# Usage:
#   ./build_macos_app.sh [options]
#
# Options:
#   --clean     Clean build and dist directories before building
#   --optimize  Optimize the build for size using UPX
#   --test      Run the application after building to verify it works
#
# Example:
#   ./build_macos_app.sh --clean --optimize

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
APP_DIR="$DIST_DIR/CryptoBot.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
FRAMEWORKS_DIR="$CONTENTS_DIR/Frameworks"
VENV_DIR="$PROJECT_ROOT/venv"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
DEV_REQUIREMENTS_FILE="$PROJECT_ROOT/requirements-dev.txt"

# Ensure we're in the project root
cd "$PROJECT_ROOT"

# Output header
echo "===================================================="
echo "CryptoBot macOS Application Bundle Build Script"
echo "===================================================="
echo "Project root: $PROJECT_ROOT"
echo "Build directory: $BUILD_DIR"
echo "Distribution directory: $DIST_DIR"
echo "Application bundle: $APP_DIR"
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
pip install py2app

if [ $OPTIMIZE -eq 1 ]; then
  # Install UPX for compression
  echo "Installing UPX for executable compression..."
  
  # Check if UPX is already installed
  if command -v upx &> /dev/null; then
    echo "UPX is already installed."
    UPX_PATH=$(command -v upx)
  else
    # Try to install UPX using Homebrew
    if command -v brew &> /dev/null; then
      echo "Installing UPX using Homebrew..."
      brew install upx
      UPX_PATH=$(command -v upx)
    else
      echo "Homebrew not found. Installing Homebrew..."
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      echo "Installing UPX using Homebrew..."
      brew install upx
      UPX_PATH=$(command -v upx)
    fi
  fi
  
  if [ -n "$UPX_PATH" ]; then
    echo "UPX installed at: $UPX_PATH"
  else
    echo "Could not install UPX. Continuing without optimization."
    OPTIMIZE=0
  fi
fi

echo "Dependencies installed."

# Create PyInstaller spec file for the main application
echo "Creating PyInstaller spec file for the main application..."
cat > "$PROJECT_ROOT/cryptobot_macos.spec" << EOF
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['$PROJECT_ROOT'],
    binaries=[],
    datas=[
        ('static', 'static'),
        ('templates', 'templates'),
        ('config', 'config'),
        ('LICENSE', '.'),
        ('README.md', '.'),
    ],
    hiddenimports=[
        'sqlalchemy.ext.baked',
        'sqlalchemy.ext.declarative',
        'redis',
        'numpy',
        'pandas',
        'fastapi',
        'uvicorn',
        'jinja2',
        'pydantic',
        'email_validator',
        'passlib.handlers.argon2',
        'cryptography',
    ],
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
    name='CryptoBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CryptoBot',
)

app = BUNDLE(
    coll,
    name='CryptoBot.app',
    icon='static/favicon.ico',
    bundle_identifier='com.cryptobot.trading',
    info_plist={
        'CFBundleName': 'CryptoBot',
        'CFBundleDisplayName': 'CryptoBot',
        'CFBundleGetInfoString': 'CryptoBot Trading System',
        'CFBundleIdentifier': 'com.cryptobot.trading',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2025 CryptoBot Team',
        'NSHighResolutionCapable': True,
        'LSBackgroundOnly': False,
        'LSEnvironment': {
            'PATH': '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin',
        },
        'NSAppleEventsUsageDescription': 'CryptoBot needs to use Apple Events for automation.',
        'NSRequiresAquaSystemAppearance': False,
    },
)
EOF

# Create PyInstaller spec file for the Quick Start Launcher
echo "Creating PyInstaller spec file for the Quick Start Launcher..."
cat > "$PROJECT_ROOT/launcher_macos.spec" << EOF
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
    name='CryptoBot Launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CryptoBot Launcher',
)

app = BUNDLE(
    coll,
    name='CryptoBot Launcher.app',
    icon='static/favicon.ico',
    bundle_identifier='com.cryptobot.launcher',
    info_plist={
        'CFBundleName': 'CryptoBot Launcher',
        'CFBundleDisplayName': 'CryptoBot Launcher',
        'CFBundleGetInfoString': 'CryptoBot Quick Start Launcher',
        'CFBundleIdentifier': 'com.cryptobot.launcher',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2025 CryptoBot Team',
        'NSHighResolutionCapable': True,
        'LSBackgroundOnly': False,
        'LSEnvironment': {
            'PATH': '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin',
        },
        'NSAppleEventsUsageDescription': 'CryptoBot Launcher needs to use Apple Events for automation.',
        'NSRequiresAquaSystemAppearance': False,
    },
)
EOF

# Run PyInstaller for the main application
echo "Building main application with PyInstaller..."
if [ $OPTIMIZE -eq 1 ]; then
  pyinstaller --clean "$PROJECT_ROOT/cryptobot_macos.spec" --upx-dir="$(dirname "$UPX_PATH")"
else
  pyinstaller --clean "$PROJECT_ROOT/cryptobot_macos.spec"
fi
echo "PyInstaller build completed for main application."

# Run PyInstaller for the Quick Start Launcher
echo "Building Quick Start Launcher with PyInstaller..."
if [ $OPTIMIZE -eq 1 ]; then
  pyinstaller --clean "$PROJECT_ROOT/launcher_macos.spec" --upx-dir="$(dirname "$UPX_PATH")"
else
  pyinstaller --clean "$PROJECT_ROOT/launcher_macos.spec"
fi
echo "PyInstaller build completed for Quick Start Launcher."

# Verify the build
if [ -d "$APP_DIR" ]; then
  echo "Application bundle built successfully."
else
  echo "Application bundle build failed!"
  exit 1
fi

# Create a symbolic link to the Applications folder
echo "Creating symbolic link to Applications folder..."
mkdir -p "$DIST_DIR/dmg_contents"
cp -R "$APP_DIR" "$DIST_DIR/dmg_contents/"
cp -R "$DIST_DIR/CryptoBot Launcher.app" "$DIST_DIR/dmg_contents/"
ln -sf /Applications "$DIST_DIR/dmg_contents/Applications"
echo "Symbolic link created."

# Create a background image for the DMG
echo "Creating background image for the DMG..."
mkdir -p "$DIST_DIR/dmg_contents/.background"
cat > "$DIST_DIR/dmg_contents/.background/background.svg" << EOF
<svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">
  <rect width="600" height="400" fill="#1a1a1a"/>
  <text x="300" y="200" font-family="Arial" font-size="48" text-anchor="middle" fill="#ffffff">CryptoBot</text>
  <text x="300" y="250" font-family="Arial" font-size="24" text-anchor="middle" fill="#ffffff">Drag to Applications folder to install</text>
</svg>
EOF

# Convert SVG to PNG
if command -v convert &> /dev/null; then
  convert -background none "$DIST_DIR/dmg_contents/.background/background.svg" "$DIST_DIR/dmg_contents/.background/background.png"
else
  echo "ImageMagick not found. Installing..."
  brew install imagemagick
  convert -background none "$DIST_DIR/dmg_contents/.background/background.svg" "$DIST_DIR/dmg_contents/.background/background.png"
fi

# Create a .DS_Store file for the DMG
echo "Creating .DS_Store file for the DMG..."
# This is a placeholder. In a real scenario, you would create a proper .DS_Store file
# to control the appearance of the DMG window.
touch "$DIST_DIR/dmg_contents/.DS_Store"

# Test the application if requested
if [ $TEST -eq 1 ]; then
  echo "Testing application..."
  open "$APP_DIR"
  echo "Application test started."
fi

# Deactivate virtual environment
deactivate
echo "Virtual environment deactivated."

# Output summary
echo "===================================================="
echo "Build Summary"
echo "===================================================="
echo "Application bundle: $APP_DIR"
echo "DMG contents: $DIST_DIR/dmg_contents"
echo "===================================================="
echo "Build completed successfully!"